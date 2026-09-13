"""Prepare a phase-consistent qNEP training/test split from a sparse-BEC extxyz.

The qNEP documentation permits ``bec:R:9`` to be present only on selected
structures.  For the phonon compatibility benchmark we deliberately train on
the cubic phase only: the GPUMD documentation warns that a BEC target is
normally appropriate for one material in one phase because the electronic
dielectric constant is held fixed.  The mixed-phase export remains the data
interface/coverage artifact; this script makes the smaller, scientifically
controlled training subset.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

from zstar.qnep_dataset import _properties, read_extxyz


def _phase(header: str) -> str:
    match = re.search(r"(?:^|\s)phase_label=([^\s]+)", header)
    return match.group(1) if match else "unknown"


def _has_bec(header: str) -> bool:
    return any(name.lower() == "bec" for name, _kind, _width in _properties(header)[1])


def _frame_key(index: int, header: str) -> tuple[int, int]:
    match = re.search(r"(?:^|\s)frame_id=(\d+)", header)
    return (int(match.group(1)) if match else index, index)


def _group_key(index: int, header: str) -> str:
    """Return the provenance group used for leakage-safe splitting.

    Finite-displacement rows from one BEC family are strongly correlated and
    must stay in one split.  The 2x2x2 supplement already carries an explicit
    parent_frame_id; older response rows encode the parent before ``::``.
    """
    match = re.search(r"(?:^|\s)parent_frame_id=([^\s]+)", header)
    if match:
        return match.group(1)
    match = re.search(r"(?:^|\s)frame_id=([^\s]+)", header)
    value = match.group(1) if match else str(index)
    return value.split("::", 1)[0]


def _write(frames, indices, output: Path) -> None:
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for index in indices:
            frame = frames[index]
            handle.write(f"{frame.natoms}\n{frame.header}\n")
            handle.write("\n".join(frame.atoms) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--phase", default="cubic")
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=20260913)
    parser.add_argument(
        "--min-test-bec-groups",
        type=int,
        default=1,
        help=(
            "minimum number of leakage-safe labelled groups in test.xyz; "
            "use 3-5 for a meaningful sparse-BEC validation set"
        ),
    )
    parser.add_argument(
        "--all-train",
        action="store_true",
        help="put every selected phase frame in train.xyz; use one duplicate parser frame in test.xyz",
    )
    args = parser.parse_args()
    if not args.all_train and not 0 < args.test_fraction < 1:
        raise SystemExit("--test-fraction must be between 0 and 1")
    if args.min_test_bec_groups < 0:
        raise SystemExit("--min-test-bec-groups must be non-negative")

    frames = read_extxyz(args.input)
    candidates = [i for i, frame in enumerate(frames) if _phase(frame.header) == args.phase]
    if len(candidates) < 10:
        raise SystemExit(f"Only {len(candidates)} frames found for phase {args.phase!r}")
    candidates.sort(key=lambda i: _frame_key(i, frames[i].header))

    if args.all_train:
        train = candidates
        # GPUMD 5.x expects test.xyz to contain at least one valid frame.  The
        # placeholder is deliberately also in train.xyz; it is never used as
        # an independent generalization estimate.
        test = [candidates[0]]
    else:
        rng = random.Random(args.seed)
        groups = {}
        for index in candidates:
            groups.setdefault(_group_key(index, frames[index].header), []).append(index)
        labeled_groups = [group for group in groups.values() if any(_has_bec(frames[i].header) for i in group)]
        unlabeled_groups = [group for group in groups.values() if not any(_has_bec(frames[i].header) for i in group)]
        rng.shuffle(labeled_groups)
        rng.shuffle(unlabeled_groups)
        n_test = max(1, round(len(candidates) * args.test_fraction))
        # Keep the requested number of labelled groups in the test split when
        # possible, then fill by whole groups until the requested frame count
        # is reached.  Whole groups avoid leakage between finite-displacement
        # rows from one BEC family; the minimum is deliberately configurable
        # because one labelled test frame is too weak for a BEC MAE claim.
        test_groups = labeled_groups[: min(args.min_test_bec_groups, len(labeled_groups))]
        labeled_groups = labeled_groups[len(test_groups) :]
        for group in unlabeled_groups + labeled_groups:
            if sum(len(item) for item in test_groups) >= n_test:
                break
            test_groups.append(group)
        test_indices = [i for group in test_groups for i in group]
        test_set = set(test_indices)
        test = sorted(test_indices, key=lambda i: _frame_key(i, frames[i].header))
        train = sorted(set(candidates) - test_set, key=lambda i: _frame_key(i, frames[i].header))

    target = Path(args.output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    _write(frames, train, target / "train.xyz")
    _write(frames, test, target / "test.xyz")
    manifest = {
        "schema": "zstar-qnep-training-split",
        "input": str(Path(args.input).resolve()),
        "phase": args.phase,
        "seed": args.seed,
        "test_fraction": args.test_fraction,
        "min_test_bec_groups": args.min_test_bec_groups,
        "all_train": args.all_train,
        "test_is_training_duplicate": bool(args.all_train),
        "train_frames": len(train),
        "test_frames": len(test),
        "train_bec_frames": sum(_has_bec(frames[i].header) for i in train),
        "test_bec_frames": sum(_has_bec(frames[i].header) for i in test),
        "train_phase_counts": dict(Counter(_phase(frames[i].header) for i in train)),
        "test_phase_counts": dict(Counter(_phase(frames[i].header) for i in test)),
        "train_frame_ids": [_frame_key(i, frames[i].header)[0] for i in train],
        "test_frame_ids": [_frame_key(i, frames[i].header)[0] for i in test],
        "train_group_ids": sorted({_group_key(i, frames[i].header) for i in train}),
        "test_group_ids": sorted({_group_key(i, frames[i].header) for i in test}),
        "group_overlap": sorted(
            {_group_key(i, frames[i].header) for i in train}
            & {_group_key(i, frames[i].header) for i in test}
        ),
        "bec_is_optional_per_frame": True,
        "purpose": "small cubic-phase qNEP compatibility benchmark, not a production model",
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
