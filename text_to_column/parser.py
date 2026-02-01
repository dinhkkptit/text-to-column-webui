#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import textfsm


@dataclass(frozen=True)
class AutoDetectResult:
    command: str
    template: str
    rows: int
    cols: int


def normalize_template(text: str) -> str:
    """
    Some community TextFSM templates are formatted in ways that TextFSM is picky about.
    This normalizer keeps Value lines/comments/blank lines intact and indents '^' rules
    inside a state block so TextFSM can compile reliably.

    Kept from your original script, slightly clarified.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    out: List[str] = []
    in_state = False
    for line in lines:
        if line.startswith("Value ") or line.strip() == "" or line.lstrip().startswith("#"):
            out.append(line)
            continue
        # A "state" line looks like: Start / SomeStateName
        if not line.startswith((" ", "\t")) and not line.startswith("^"):
            in_state = True
            out.append(line)
            continue
        # If we are inside a state, ensure regex rules are indented
        if line.startswith("^") and in_state:
            out.append("  " + line)
            continue
        out.append(line)
    return "\n".join(out).rstrip() + "\n"


def parse_with_template(template_path: Path, raw: str) -> Dict[str, Any]:
    """
    Parse raw command output with a TextFSM template.

    Returns:
      {
        "headers": [..original headers..],
        "rows": [ {header_lower: value, ...}, ...]
      }
    """
    tpl = normalize_template(template_path.read_text(encoding="utf-8", errors="replace"))
    fsm = textfsm.TextFSM(io.StringIO(tpl))
    parsed = fsm.ParseText(raw)
    headers = list(fsm.header)
    rows = [{headers[i].lower(): row[i] for i in range(len(headers))} for row in parsed]
    return {"headers": headers, "rows": rows}


def build_command_prefixes(platform_map: Dict[str, str]) -> List[Tuple[str, str]]:
    """
    Convert mapping keys like "show cdp neighbors" to filename-friendly prefixes:
      "show_cdp_neighbors"

    Return list of (cmd_prefix_underscored, mapping_key_original) sorted by longest first.
    """
    items: List[Tuple[str, str]] = []
    for k in platform_map.keys():
        prefix = k.strip().lower().replace(" ", "_")
        items.append((prefix, k))
    items.sort(key=lambda x: len(x[0]), reverse=True)
    return items


def split_command_and_hostname(filename_stem: str, cmd_prefixes: List[Tuple[str, str]]) -> Optional[Tuple[str, str, str]]:
    """
    Given stem like:
      show_cdp_neighbors_ciscol224_L2_1

    Find the longest command prefix that matches at the start, followed by "_".
    Return (cmd_prefix_underscored, hostname, mapping_key_original)
    """
    s = filename_stem.lower()
    for cmd_prefix, orig_key in cmd_prefixes:
        if s.startswith(cmd_prefix + "_"):
            hostname = filename_stem[len(cmd_prefix) + 1:]  # keep original case for hostname
            return cmd_prefix, hostname, orig_key
    return None


def load_mapping(mapping_path: Path) -> Dict[str, Dict[str, str]]:
    return json.loads(mapping_path.read_text(encoding="utf-8"))


def load_platform_aliases(config_path: Path) -> Dict[str, str]:
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8")).get("platform_aliases", {})


def list_platforms(repo_root: Path, root_dir: str = "files") -> List[str]:
    """
    For UI: list folder names under <root_dir>/ (these are "platform folders").
    """
    root = repo_root / root_dir
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])


def list_commands_for_platform(
    mapping: Dict[str, Dict[str, str]],
    platform: str,
    aliases: Optional[Dict[str, str]] = None,
) -> List[str]:
    """
    For UI: list mapping keys ("show ip int br", etc.) for a platform (after alias resolution).
    """
    aliases = aliases or {}
    resolved = aliases.get(platform, platform)
    platform_map = mapping.get(resolved, {})
    return sorted(platform_map.keys())


def resolve_template_name(
    mapping: Dict[str, Dict[str, str]],
    platform: str,
    command: str,
    aliases: Optional[Dict[str, str]] = None,
) -> str:
    aliases = aliases or {}
    resolved = aliases.get(platform, platform)
    platform_map = mapping.get(resolved, {})
    if not platform_map:
        raise KeyError(f"No mapping for platform '{resolved}' (folder '{platform}')")
    if command not in platform_map:
        raise KeyError(f"No mapping for command '{command}' in platform '{resolved}'")
    return platform_map[command]


def parse_text(
    repo_root: Path,
    platform: str,
    command: str,
    raw_text: str,
    templates_dir: str = "templates",
    mapping_file: str = "mapping.json",
    config_file: str = "config.json",
) -> Dict[str, Any]:
    """
    Parse raw CLI text using mapping.json + TextFSM template.

    Returns:
      {
        "platform_folder": "<platform>",
        "platform_resolved": "<resolved>",
        "command": "<command>",
        "template": "<template file name>",
        "headers": [...],
        "rows": [...]
      }
    """
    mapping = load_mapping(repo_root / mapping_file)
    aliases = load_platform_aliases(repo_root / config_file)
    resolved = aliases.get(platform, platform)

    tpl_name = resolve_template_name(mapping, platform, command, aliases=aliases)
    tpl_path = repo_root / templates_dir / tpl_name
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template not found: {tpl_path}")

    parsed = parse_with_template(tpl_path, raw_text)
    return {
        "platform_folder": platform,
        "platform_resolved": resolved,
        "command": command,
        "template": tpl_name,
        "headers": [h.lower() for h in parsed["headers"]],
        "rows": parsed["rows"],
    }


def get_template_preview(
    repo_root: Path,
    platform: str,
    command: str,
    templates_dir: str = "templates",
    mapping_file: str = "mapping.json",
    config_file: str = "config.json",
) -> Dict[str, str]:
    """Return the resolved template filename and the template text for UI preview."""
    mapping = load_mapping(repo_root / mapping_file)
    aliases = load_platform_aliases(repo_root / config_file)

    tpl_name = resolve_template_name(mapping, platform, command, aliases=aliases)
    tpl_path = repo_root / templates_dir / tpl_name
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template not found: {tpl_path}")

    raw_tpl = tpl_path.read_text(encoding="utf-8", errors="replace")
    return {"template": tpl_name, "normalized": normalize_template(raw_tpl), "raw": raw_tpl}


def autodetect_command(
    repo_root: Path,
    platform: str,
    raw_text: str,
    templates_dir: str = "templates",
    mapping_file: str = "mapping.json",
    config_file: str = "config.json",
    max_templates: int = 200,
) -> AutoDetectResult:
    """
    Try multiple templates for a platform and pick the best match.

    Heuristic: choose the template that yields the most rows; tie-breaker is most columns.
    Only templates that compile and return at least 1 row are considered.
    """
    mapping = load_mapping(repo_root / mapping_file)
    aliases = load_platform_aliases(repo_root / config_file)
    resolved = aliases.get(platform, platform)

    platform_map: Dict[str, str] = mapping.get(resolved, {})
    if not platform_map:
        raise KeyError(f"No mapping for platform '{resolved}' (folder '{platform}')")

    best: Optional[AutoDetectResult] = None
    tried = 0

    for command, tpl_name in platform_map.items():
        if tried >= max_templates:
            break
        tried += 1

        tpl_path = repo_root / templates_dir / tpl_name
        if not tpl_path.exists():
            continue

        try:
            parsed = parse_with_template(tpl_path, raw_text)
        except Exception:
            continue

        rows_n = len(parsed.get("rows", []))
        cols_n = len(parsed.get("headers", []))
        if rows_n <= 0:
            continue

        candidate = AutoDetectResult(command=command, template=tpl_name, rows=rows_n, cols=cols_n)
        if best is None:
            best = candidate
            continue

        if (candidate.rows, candidate.cols) > (best.rows, best.cols):
            best = candidate

    if best is None:
        raise ValueError(
            f"Auto-detect could not find a template that produces rows for platform '{resolved}'. "
            "(Tip: ensure you're pasting full command output and correct platform.)"
        )
    return best



def infer_hostname(filename: str) -> str:
    """Infer hostname from an uploaded filename.

    Expected patterns:
      - <anything>_<hostname>.txt  -> hostname is last '_' token
      - <command>__<hostname>.txt  -> if '__' present, hostname is text after last '__'

    Falls back to full stem if it cannot split.
    """
    stem = Path(filename).stem or filename
    if "__" in stem:
        parts = stem.split("__")
        return parts[-1] or stem
    parts = stem.split("_")
    return parts[-1] if len(parts) >= 2 and parts[-1] else stem


def command_to_slug(command: str) -> str:
    """Convert a CLI command string into a filename slug.

    Example:
      "show lb vserver" -> "show_lb_vserver"
    """
    parts = [p for p in command.strip().lower().split() if p]
    return "_".join(parts)


def infer_hostname_after_command(filename: str, command: str) -> str:
    """Infer hostname as the **longest** text after the command slug.

    This is used for *combined CSV* batch mode.

    Example:
      filename: show_lb_vserver_netscaler1_L4_1.txt
      command:  show lb vserver
      -> hostname: netscaler1_L4_1

    If the filename doesn't start with the command slug, falls back to infer_hostname().
    """
    stem = Path(filename).stem or filename
    slug = command_to_slug(command)

    s = stem.lower()
    p = slug.lower()

    if p and s.startswith(p):
        rest = stem[len(slug):]
        rest = rest.lstrip("_")
        if rest:
            return rest

    return infer_hostname(filename)


def rows_to_csv(headers: List[str], rows: List[Dict[str, Any]]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=headers)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return out.getvalue()


def parse_folder_to_csv(
    repo_root: Path,
    root_dir: str = "files",
    templates_dir: str = "templates",
    mapping_file: str = "mapping.json",
    config_file: str = "config.json",
    out_dir: str = "files",
    only_platform: str = "",
) -> List[str]:
    """
    Backwards-compatible behavior for the original CLI script:
    - read <root_dir>/<platform>/*.txt
    - filename format: <command>_<hostname>.txt with underscores used for command spaces
    - choose templates by longest prefix match against mapping keys
    - write per-command CSV: <resolved_platform>_<command_prefix>.csv into <out_dir>/

    Returns list of output filenames written.
    """
    mapping = load_mapping(repo_root / mapping_file)
    aliases = load_platform_aliases(repo_root / config_file)

    root = repo_root / root_dir
    if not root.exists():
        raise FileNotFoundError(f"Root folder not found: {root}")

    platform_dirs = [p for p in root.iterdir() if p.is_dir()]
    if only_platform:
        platform_dirs = [root / only_platform]

    written: List[str] = []

    for platform_dir in sorted(platform_dirs):
        folder_platform = platform_dir.name
        resolved_platform = aliases.get(folder_platform, folder_platform)

        platform_map: Dict[str, str] = mapping.get(resolved_platform, {})
        if not platform_map:
            # Keep behavior: skip silently-ish
            continue

        cmd_prefixes = build_command_prefixes(platform_map)
        per_cmd = defaultdict(list)

        for txt in sorted(platform_dir.glob("*.txt")):
            stem = txt.stem
            split = split_command_and_hostname(stem, cmd_prefixes)
            if not split:
                continue

            cmd_part, hostname, mapping_key = split
            tpl_name = platform_map[mapping_key]
            tpl_path = repo_root / templates_dir / tpl_name
            if not tpl_path.exists():
                continue

            raw = txt.read_text(encoding="utf-8", errors="replace")
            try:
                parsed = parse_with_template(tpl_path, raw)
            except Exception:
                continue

            for r in parsed["rows"]:
                r["hostname"] = hostname
                per_cmd[cmd_part].append(r)

        outp = repo_root / out_dir
        outp.mkdir(parents=True, exist_ok=True)

        for cmd_part, rows in sorted(per_cmd.items()):
            # stable column order: hostname first, then others discovered
            cols: List[str] = []
            for r in rows:
                for k in r:
                    if k != "hostname" and k not in cols:
                        cols.append(k)

            out_name = f"{resolved_platform}_{cmd_part}.csv"
            out_path = outp / out_name

            with out_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["hostname"] + cols)
                w.writeheader()
                for r in rows:
                    w.writerow(r)

            written.append(out_name)

    return written
