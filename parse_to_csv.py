#!/usr/bin/env python3
import argparse
from pathlib import Path

from text_to_column.parser import parse_folder_to_csv


def main():
    ap = argparse.ArgumentParser(
        description="Parse files/<platform> with filenames: <command>_<hostname>.txt (hostname may contain underscores)"
    )
    ap.add_argument("--root", default="files")
    ap.add_argument("--templates-dir", default="templates")
    ap.add_argument("--mapping", default="mapping.json")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out-dir", default="files")
    ap.add_argument("--platform", default="", help="Optional: only parse one platform folder")
    args = ap.parse_args()

    repo_root = Path(".").resolve()

    written = parse_folder_to_csv(
        repo_root=repo_root,
        root_dir=args.root,
        templates_dir=args.templates_dir,
        mapping_file=args.mapping,
        config_file=args.config,
        out_dir=args.out_dir,
        only_platform=args.platform,
    )

    for name in written:
        print(f"Wrote {name}")


if __name__ == "__main__":
    main()
