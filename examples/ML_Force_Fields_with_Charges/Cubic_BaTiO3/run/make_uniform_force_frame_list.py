"""Write an explicit frame list for the uniform DFT force campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    excluded = set(args.exclude)
    frame_ids = [record["frame_id"] for record in manifest["records"] if record["frame_id"] not in excluded]
    if len(frame_ids) != len(set(frame_ids)):
        raise SystemExit("duplicate frame_id in manifest")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(f"frame-{frame_id}\n" for frame_id in frame_ids), encoding="utf-8")
    print(json.dumps({"requested": len(manifest["records"]), "excluded": sorted(excluded), "submitted": len(frame_ids)}, indent=2))


if __name__ == "__main__":
    main()
