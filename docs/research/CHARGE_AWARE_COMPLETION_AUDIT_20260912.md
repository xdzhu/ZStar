# Charge-aware compatibility completion audit

This audit records the current evidence without promoting unfinished work to a
completed qNEP application. It is kept on the development branch
`codex/qnep-charge-aware-compatibility`.

| Requirement | Evidence | Status |
| --- | --- | --- |
| Freeze v1 and isolate changes | Branch from freeze commit `6748e50`; pre-existing worktree edits preserved | complete |
| Generic charge-aware frame schema | `zstar/charge_aware_dataset.py`, explicit BEC availability and `(N,3,3)` validation | complete |
| DeepMD representative-frame input | `read_deepmd_dataset`, metadata temperature/phase/charge/split support | complete |
| MACE/ASE and other force-field input | extended-XYZ adapter with `REF_*` and `dft_*` aliases | complete |
| Reproducible temperature/phase selection | `zstar data select`, fixed seed and stratified selection tests | complete |
| Controlled force pool | `results/sample_dataset/qnep_bto_force_pool250.jsonl`, 250 source rows with duplicate-geometry validation enabled; all routine BEC candidates are present | complete with duplicate audit |
| Phase-target candidate design | 13 rhombohedral + 14 orthorhombic + 20 tetragonal + 20 cubic primitive/displacement frames; no duplicate padding; supercell padding rejected for routine BEC because it creates hundreds of displacements | complete |
| Sparse BEC campaign | Original WZ array `44130012` was followed by MPI-PYATB recovery arrays `44206174` (primary), `44206175` (addon), `44206275` (frame 524), and final recovery `44212769` (frames 565 and 567); anomalous node `j10r2n12` is excluded and all recovery jobs use 32 MPI ranks x 1 thread | complete (65 parent families collected; 62 unique BEC labels retained in the 249-frame export; frames 13, 560, 564 explicitly unlabeled) |
| Incomplete-frame gate | Frame 13 has a missing ABACUS final-time marker in one displacement log and is skipped by the collector rather than assigned a placeholder BEC | active safeguard |
| Force-only reuse from BEC SCFs | `collect_bec_batch.py --force-only-output` extracted 612 ABACUS/PBEsol energy-force rows from 65 complete parent families; incomplete families are withheld and the neutral manifest is checked in | complete (raw JSONL remains scratch-only) |
| Compact cluster-result transport | `run/compact_wuzhen_bec_outputs.py` retains only structures, PYATB polarization, response manifest, final energy, and final force blocks; Wuzhen Python 3.6 archive was re-read locally and passed BEC collection | complete (pilot) |
| qNEP-compatible export | `zstar data export`, sparse `bec:R:9`, round-trip and manifest tests | complete |
| qNEP/GPUMD phonon/NAC evidence | Final 167-frame/21-BEC cubic-only model, held-out E/F/BEC metrics, and separate without-NAC/with-NAC DFT overlays are checked in | complete (Level 2 cost-capped benchmark) |
| GPU finite-temperature MD / Figure 5 | No converged qNEP MD campaign or Figure 5 reproduction claimed | not run |
| Local regression suite | Latest `python -m pytest -q` -> `425 passed` in 48.11 s; `zstar data --help`, `zstar qnep --help`, `data validate` on the 249-frame export, and `qnep check` report valid | complete |

## Finalization gate for the WZ campaign

The final collection gate is now closed. Evidence retained for audit is:

1. `sacct` shows every selected frame-level recovery task (including
   `44206175`, `44206275`, and the final `44212769`) completed with exit code
   0; historical parent-array failures are retained in provenance and are not
   treated as successful frame labels;
2. the collector reports 65 complete parent families; only source parents
   `13`, `560`, and `564` are skipped and remain explicitly unlabeled;
3. the BEC coverage report and frame-level provenance manifest are regenerated;
4. the full force pool is annotated through `zstar data annotate` and exported
   with `zstar data export`;
5. the dataset, qNEP export, and documentation are revalidated.

The CPC claim remains a charge-aware compatibility workflow plus a Level 2
small-model phonon/NAC benchmark, not a production qNEP model or a
finite-temperature application.  The GPU budget is intentionally capped at
one A30 and 10,000 generations; the measured test force MAE is 0.2779 eV/A,
so extending the run is not silently treated as completed work.

## 40-atom cubic-BTO supplement (completed collection)

The continuation used exactly two selected 40-atom P1 cubic frames and forward
differences only: 120 positive phonon displacements per frame, 240 stages
total.  The final audit found all 240 polarization outputs and an empty queue.
The old 480-stage central-difference attempt is archived and excluded from all
labels.  Compact collection produced 242 force-only rows (including the two
parent reference rows) and two 40-atom BEC annotations.  The resulting pure
PBEsol cubic dataset contains 167 frames (117 five-atom and 50 forty-atom)
with 21 explicit BEC-labelled frames; missing BEC remains explicit rather
than zero-filled.

During the final tail of the array, `44250980_139` was the only observed
slow-node anomaly: it stalled on oversubscribed `j11r2n24` and was replaced by
`44253559_139` with that node quarantined.  Its partial output remains
archived and is not used as a label.

The first retry also exposed a missing stage-local UPF/orbital symlink during
manual reconstruction; that failed directory was archived and the symlinks
were restored from the original stage.  The corrected retry is
`44253862_139`.  A missing-output audit additionally queued indices 60, 61,
63, 64, 66, 67, 68, 89, and 90 as `44253895`; these are replacement runs, not
new dataset stages.

The stage-list audit uses zero-based indices.  After `44253895` completed, the
only remaining missing outputs were indices 59, 62, 65, 208, and 209; these
were submitted as `44254274` and all completed successfully.  The replacement
arrays are bookkeeping for incomplete outputs and do not expand the 240-stage
campaign.  The final qNEP run is deliberately limited to one A30 and 10k
generations initially; it is not a production-force-field claim.
