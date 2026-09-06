"""Export citation numbers from a compiled LaTeX bibliography, without defaults."""

import argparse
import json
from pathlib import Path
import re


def bibliography_labels(bbl: Path) -> dict[str, int]:
    keys = re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", bbl.read_text(encoding="utf-8"))
    if not keys or len(keys) != len(set(keys)):
        raise ValueError("Bibliography is empty or has duplicate citation keys")
    return {key: number for number, key in enumerate(keys, 1)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bbl", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(bibliography_labels(args.bbl), indent=2) + "\n",
                           encoding="utf-8")
