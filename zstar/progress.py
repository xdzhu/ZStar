"""Flushed, scheduler-friendly workflow progress messages."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def progress(stage: str, component: str, status: str, message: str,
             *, log_path: Path | None = None) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"[{timestamp}] [{stage}] [{component}] [{status}] {message}"
    print(line, flush=True)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
