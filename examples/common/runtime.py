"""Resolve example launch commands using the installed ZStar configuration."""

import os
from pathlib import Path
import sys

from zstar.configuration import launcher_command, resolve_parallelism


def commands(root):
    _, threads = resolve_parallelism(root)
    omp = int(os.environ.get("OMP_NUM_THREADS", threads))
    if omp < 1:
        raise ValueError("OMP_NUM_THREADS must be positive")
    return (
        os.environ.get("ABACUS_COMMAND") or launcher_command("abacus", root=root),
        os.environ.get("PYATB_COMMAND") or launcher_command("pyatb", root=root),
        str(omp),
    )


if __name__ == "__main__":
    print("\n".join(commands(Path(sys.argv[1]).resolve())))
