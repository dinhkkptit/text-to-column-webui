#!/usr/bin/env python3
import argparse
import csv
import io
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple

import textfsm


def normalize_template(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    out, in_state = [], False
    for line in lines:
        if line.startswith("Value ") or line.strip() == "" or line.lstrip().startswith("#"):
            out.append(line); continue
        if not line.startswith((" ", "\t")) and not line.startswith("^"):
            in_state = True; out.append(line); continue
        if line.startswith("^") and in_state:
            out.append("  " + line); continue
        out.append(line)
    return "\n".join(out).rstrip() + "\n"


def parse_text(template_path: Path, raw: str) -> List[Dict[str, Any]]:
    tpl = normalize_template(template_path.read_text(encoding="utf-8", errors="replace"))
    fsm = textfsm.TextFSM(io.StringIO(tpl))
    rows = fsm.ParseText(raw)
    headers = fsm.header
    return [{headers[i].lower(): r[i] for i in range(len(headers))} for r in rows]


def write_csv(path: Path, rows: List[Dict[str, Any]]):
    cols: List[str] = []
    for r in rows:
        for k in r:
            if k != "hostname" and k not in cols:
                cols.append(k)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["hostname"] + cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def build_command_prefixes(platform_map: Dict[str, str]) -> List[Tuple[str, str]]:
    """
    Convert mapping keys like "show cdp neighbors" to filename-friendly prefixes:
      "show_cdp_neighbors"

    Return list of (cmd_prefix_underscored, mapping_key_original) sorted by longest first.
    """
    items = []
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
    Return (cmd_part_underscored, hostname, mapping_key_original)
    """
    s = filename_stem.lower()
    for cmd_prefix, orig_key in cmd_prefixes:
        if s.startswith(cmd_prefix + "_"):
            hostname = filename_stem[len(cmd_prefix) + 1:]  # keep original case for hostname
            return cmd_prefix, hostname, orig_key
    return None


def resolve_template(platform_map: Dict[str, str], mapping_key_original: str) -> str:
    return platform_map[mapping_key_original]


def main():
    ap = argparse.ArgumentParser(description="Parse samples_txt/<platform> with filenames: <command>_<hostname>.txt where hostname may contain underscores")
    ap.add_argument("--root", default="files")
    ap.add_argument("--templates-dir", default="templates")
    ap.add_argument("--mapping", default="mapping.json")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out-dir", default="files")
    ap.add_argument("--platform", default="", help="Optional: only parse one platform folder")
    args = ap.parse_args()

    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    aliases = {}
    cfg = Path(args.config)
    if cfg.exists():
        aliases = json.loads(cfg.read_text(encoding="utf-8")).get("platform_aliases", {})

    root = Path(args.root)
    platform_dirs = [p for p in root.iterdir() if p.is_dir()]
    if args.platform:
        platform_dirs = [root / args.platform]

    for platform_dir in sorted(platform_dirs):
        folder_platform = platform_dir.name
        resolved_platform = aliases.get(folder_platform, folder_platform)

        platform_map: Dict[str, str] = mapping.get(resolved_platform, {})
        if not platform_map:
            print(f"SKIP: No mapping for platform '{resolved_platform}' (folder '{folder_platform}')")
            continue

        cmd_prefixes = build_command_prefixes(platform_map)
        per_cmd = defaultdict(list)

        for txt in sorted(platform_dir.glob("*.txt")):
            stem = txt.stem
            split = split_command_and_hostname(stem, cmd_prefixes)
            if not split:
                # doesn't match any known command prefix
                continue

            cmd_part, hostname, mapping_key = split
            tpl_name = resolve_template(platform_map, mapping_key)
            tpl_path = Path(args.templates_dir) / tpl_name
            if not tpl_path.exists():
                print(f"ERROR: template not found: {tpl_path}")
                continue

            raw = txt.read_text(encoding="utf-8", errors="replace")
            try:
                records = parse_text(tpl_path, raw)
            except Exception as e:
                print(f"ERROR: parse failed for {txt.name} using {tpl_name}: {e}")
                continue

            for r in records:
                r["hostname"] = hostname
                per_cmd[cmd_part].append(r)

        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for cmd_part, rows in sorted(per_cmd.items()):
            out_name = f"{resolved_platform}_{cmd_part}.csv"
            write_csv(out_dir / out_name, rows)
            print(f"Wrote {out_name} ({len(rows)} rows)")

if __name__ == "__main__":
    main()
