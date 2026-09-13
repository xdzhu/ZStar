"""Write reference and displacement stage lists for parallel BEC collection."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-root", required=True, type=Path)
    parser.add_argument("--reference-output", required=True, type=Path)
    parser.add_argument("--displacement-output", required=True, type=Path)
    args = parser.parse_args()
    frames = sorted(args.batch_root.glob("frame-*"), key=lambda path: path.name)
    if not frames:
        raise SystemExit("no frame-* directories found")
    references = []
    displacements = []
    for frame in frames:
        frame_id = frame.name[len("frame-"):]
        reference = frame / "0.no-move"
        if not reference.is_dir():
            raise SystemExit(f"missing reference stage: {reference}")
        references.append(f"{frame_id} 0.no-move")
        stages = sorted(frame.glob("disp-*"), key=lambda path: int(path.name.split("-", 1)[1]))
        if not stages:
            raise SystemExit(f"missing displacement stages: {frame}")
        displacements.extend(f"{frame_id} {stage.name}" for stage in stages)
    for path, lines in (
        (args.reference_output, references),
        (args.displacement_output, displacements),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"reference_stages={len(references)} displacement_stages={len(displacements)}")


if __name__ == "__main__":
    main()
