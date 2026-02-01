from pathlib import Path
import io
import zipfile

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from text_to_column.parser import (
    load_mapping,
    load_platform_aliases,
    list_platforms,
    list_commands_for_platform,
    parse_text,
    get_template_preview,
    autodetect_command,
    rows_to_csv,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(title="text-to-column Web UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the static UI
STATIC_DIR = REPO_ROOT / "webapp" / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/platforms")
def api_platforms():
    # platform folders under files/
    return {"platforms": list_platforms(REPO_ROOT, root_dir="files")}


@app.get("/api/commands/{platform}")
def api_commands(platform: str):
    mapping = load_mapping(REPO_ROOT / "mapping.json")
    aliases = load_platform_aliases(REPO_ROOT / "config.json")
    return {"commands": list_commands_for_platform(mapping, platform, aliases=aliases)}


class ParseRequest(BaseModel):
    platform: str
    command: str = ""
    text: str
    output: str = "json"  # json|csv
    autodetect: bool = False


@app.post("/api/parse")
def api_parse(req: ParseRequest):
    if len(req.text) > 2_000_000:
        raise HTTPException(status_code=413, detail="Input too large (max 2MB).")

    try:
        command = req.command
        if req.autodetect:
            best = autodetect_command(REPO_ROOT, platform=req.platform, raw_text=req.text)
            command = best.command

        if not command:
            raise ValueError("command is required unless autodetect=true")

        parsed = parse_text(
            repo_root=REPO_ROOT,
            platform=req.platform,
            command=command,
            raw_text=req.text,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if req.output.lower() == "csv":
        # stable header order: hostname first if exists, then remaining
        headers = list(dict.fromkeys(parsed["headers"]))  # de-dup preserving order
        if "hostname" in headers:
            headers.remove("hostname")
            headers = ["hostname"] + headers
        return {"csv": rows_to_csv(headers, parsed["rows"]), "headers": headers}

    return parsed


@app.get("/api/template_preview")
def api_template_preview(platform: str, command: str):
    try:
        return get_template_preview(REPO_ROOT, platform=platform, command=command)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/autodetect")
def api_autodetect(req: ParseRequest):
    """Return the best-matching command/template + parsed output."""
    if len(req.text) > 2_000_000:
        raise HTTPException(status_code=413, detail="Input too large (max 2MB).")

    try:
        best = autodetect_command(REPO_ROOT, platform=req.platform, raw_text=req.text)
        parsed = parse_text(
            repo_root=REPO_ROOT,
            platform=req.platform,
            command=best.command,
            raw_text=req.text,
        )
        parsed["autodetect"] = {"command": best.command, "template": best.template, "rows": best.rows, "cols": best.cols}
        return parsed
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/batch_parse")
async def api_batch_parse(
    platform: str = Form(...),
    command: str = Form(""),
    autodetect: bool = Form(False),
    files: list[UploadFile] = File(...),
):
    """Parse multiple uploaded .txt files and return a ZIP of per-file CSVs (plus summary.json)."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    zbuf = io.BytesIO()
    summary = []

    with zipfile.ZipFile(zbuf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        for up in files:
            raw_bytes = await up.read()
            if len(raw_bytes) > 2_000_000:
                summary.append({"file": up.filename, "ok": False, "error": "Input too large (max 2MB per file)."})
                continue

            raw_text = raw_bytes.decode("utf-8", errors="replace")
            try:
                use_cmd = command
                if autodetect:
                    best = autodetect_command(REPO_ROOT, platform=platform, raw_text=raw_text)
                    use_cmd = best.command
                if not use_cmd:
                    raise ValueError("command is required unless autodetect=true")

                parsed = parse_text(REPO_ROOT, platform=platform, command=use_cmd, raw_text=raw_text)

                headers = list(dict.fromkeys(parsed["headers"]))
                if "hostname" in headers:
                    headers.remove("hostname")
                    headers = ["hostname"] + headers

                csv_text = rows_to_csv(headers, parsed["rows"])

                stem = (Path(up.filename).stem or "output")
                out_name = f"{stem}.csv"
                z.writestr(out_name, csv_text)
                summary.append({
                    "file": up.filename,
                    "ok": True,
                    "command": parsed.get("command"),
                    "template": parsed.get("template"),
                    "rows": len(parsed.get("rows", [])),
                    "out": out_name,
                })
            except Exception as e:
                summary.append({"file": up.filename, "ok": False, "error": str(e)})

        z.writestr("summary.json", __import__("json").dumps(summary, indent=2))

    zbuf.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="parsed_csvs.zip"'}
    return StreamingResponse(zbuf, media_type="application/zip", headers=headers)
