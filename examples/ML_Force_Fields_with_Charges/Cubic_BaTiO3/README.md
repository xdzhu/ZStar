# Charge-aware ML force-field compatibility: cubic BaTiO3

This is a compact charge-aware compatibility benchmark. It demonstrates the
ZStar side of a qNEP workflow and includes a deliberately small, cubic-phase
qNEP training run; it does not claim production accuracy or reproduce qNEP
Figure 5. The canonical current training input is the DFT-only
`results/qnep_training/dft_only_cubic_173.jsonl`: 169 unique completed
ABACUS/PBEsol frames (119 primitive and 50 2x2x2), with 2 sparse BEC labels
and 167 explicit missing-BEC states. The older 249-frame public-source export
is retained only as an interface fixture and is excluded from final training.
Missing BECs are represented by `born_effective_charges_available: false` and
`null`, never by a zero matrix.

The sample spans 50--600 K in the same temperature-coverage spirit as the
published qNEP BaTiO3 dataset and includes cubic reference, rattled, and soft
mode structures. It is not the 1832-structure/36,540-atom qNEP dataset.

For a practical user study, the recommended scale is 200--500 force-field
frames and 50--100 BEC-labelled representative frames. The DFT-only input is
the compact evidence dataset; the synthetic smoke dataset remains available
for fast CI tests.

### Selecting from a DeepMD dataset

ZStar can read a standard `deepmd/npy` directory directly. Keep temperature and
phase labels in a small sidecar CSV rather than encoding them in directory
names:

```text
frame_id,temperature,phase_label
0,300,cubic
1,500,cubic
```

Then run:

```bash
zstar data select --input /path/to/deepmd_npy \
  --metadata /path/to/frame_metadata.csv \
  --output results/selected_bec/selected.jsonl \
  --count 100 --seed 17 --temperature-bin 300 --temperature-bin 500
```

The selected JSONL retains the DeepMD coordinates, forces, energies and
virials, and can be used to generate the corresponding ZStar BEC workflow.
After the external BEC calculations finish, attach them with a
`frame_id,bec` mapping and continue with `zstar data annotate`, `validate`, and
`export`.

The same commands accept an ASE extended-XYZ source, including typical MACE
exports using `REF_energy`, `REF_forces`, and `REF_stress`. This is only an
input-format adapter; the representative selection and high-throughput BEC
calculation are shared with DeepMD and qNEP sources.

For the public qNEP extended-XYZ structure archive, use
`run/select_qnep_bto_frames.py` to create a reproducible phase-stratified
subset and `run/prepare_bec_batch.py` to generate one ZStar BEC workflow per
selected frame. The public archive does not carry an MD temperature for every
configuration, so the helper records space-group phase labels and leaves the
temperature field unset instead of fabricating temperatures. Once a source
temperature sidecar is available, the same generic selector supports
temperature strata. The helper defaults to primitive five-atom structures and
excludes source displacement snapshots/supercells; these can be enabled
explicitly when they are scientifically desired. On Wuzhen,
`run/wuzhen_bec_array.slurm` is the native
Slurm array driver; set `BATCH_ROOT`, `PYATB`, and `ABACUS_ROOT` at submission.
For recovery arrays, use `run/submit_wuzhen_bec_array.sh`; it derives the
array length from `frame_ids.txt`, launches ABACUS and PYATB with 32 MPI ranks
and one thread per rank, and excludes the quarantined node `j10r2n12`.
The driver injects each frame's own cell into the PYATB input, which is
required when the selected structures are strained or rattled.
The older public force pool and its
`results/qnep_export/train_qnep_249_sparse62.xyz` export are retained as
reproducible format fixtures only. They are phase-labelled but not
temperature-resolved; no temperatures are invented and their force/energy
labels are excluded from the current DFT-only model. Reaching 20 structures in source-limited rhombohedral and
orthorhombic phases by enabling supercells would introduce 120-atom cells and
`bec pre --method forward` creates 3N=120 positive displacements for each
selected 40-atom P1 cubic frame; central differences (240) are not used.

## Run the interface benchmark

From the repository root:

```bash
cd examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3
bash run/run.sh
```

The script uses only relative paths and writes small JSON/XYZ reports under
`results/`. Equivalent commands are:

```bash
zstar data inspect --input results/sample_dataset/dataset.jsonl
zstar data validate --input results/sample_dataset/dataset.jsonl --report results/validation/report.json
zstar data select --input results/sample_dataset/dataset.jsonl --output results/selected_bec/selected.jsonl --count 4 --seed 7 --temperature-bin 300 --temperature-bin 500
zstar data export --input results/selected_bec/selected.jsonl --output results/qnep_export/train.xyz
zstar qnep check --input results/qnep_export/train.xyz --audit-output results/qnep_export/audit.json
python run/plot_bec_coverage.py --input results/selected_bec/annotated.jsonl --output results/figures/cubic_BaTiO3_BEC_coverage.png
```

The completed compact result can be checked directly with:

```bash
zstar data validate --input results/qnep_export/train_qnep_249_sparse62.xyz \
  --report results/validation/qnep_train_249_validate.json
zstar qnep check --input results/qnep_export/train_qnep_249_sparse62.xyz \
  --audit-output results/qnep_export/qnep_train_249_audit.json
```

The first command is intended for the JSONL source before export; the checked
in validation report corresponds to the same 249-frame source dataset.

For the phonon panel, the example splits the DFT-only 169-frame input by
parent/correlation group into a cubic-only train/test set and trains a small
GPUMD qNEP `charge_mode 1` model. GPUMD is then run with `compute_phonon 0.01` (an 8×8×8 cell is used to
respect the documented many-body force-constant cutoff) and with
`dump_xyz ... force bec`. The three symmetry-reduced displacements are also
collected into a Phonopy `FORCE_SETS`; the equilibrium qNEP BEC dump plus the
DFT electronic dielectric scalar are written to `BORN`, and Phonopy applies
the NAC on the archived Γ–X–M–Γ–R–X path. This is the same tool separation
described in the qNEP paper: GPUMD supplies qNEP forces/BECs and Phonopy
constructs the harmonic NAC bands. No finite-temperature MD is claimed.

Recompute BECs with an existing ZStar ABACUS/PYATB BEC workflow, place one
source file per selected frame in `results/selected_bec/`, and provide a CSV
with `frame_id,bec` columns to `zstar data annotate`. ABACUS, pseudopotential,
orbital, k-point, cutoff, exchange-correlation functional, coordinate
convention, and atom order are provenance fields and must be kept consistent
before comparing absolute BEC values. ABACUS species blocks may use a
canonical Ba/Ti/O order; `zstar data annotate` maps labeled BEC tensors back
to the source frame order and records the reordering explicitly instead of
silently changing atom identities.

### Reusing the BEC SCFs as force-only frames

Each complete finite-displacement BEC family already contains an ABACUS SCF
energy and force for the reference and displaced structures. The collector can
export those labels without pretending that the displacement frames have BEC:

```bash
python run/collect_bec_batch.py \
  --selected results/selected_bec/selected.jsonl \
  --batch-root /path/to/bec_batch \
  --output results/selected_bec/annotated.jsonl \
  --map-output results/validation/bec_map.csv \
  --report results/validation/bec_collection.json \
  --force-only-output results/validation/bec_force_only.jsonl \
  --resume
```

The auxiliary JSONL contains one `0.no-move` frame and all completed
`disp-*` frames per accepted parent. Every row has
`born_effective_charges_available: false`, a `parent_frame_id`, a displacement
identifier/vector, and the SCF provenance. The collector rejects a partially
completed family rather than emitting a partial force set. These correlated
finite-displacement rows must be split by `parent_frame_id`; they are useful
force-only support data, not an independent random validation set. The completed
Wuzhen campaign yields 612 force/energy support rows from 65 complete BEC
parents. Three source parents (13, 560, 564) remain explicitly unlabelled
because their BEC families were incomplete; they are not padded with zero
tensors. The neutral campaign and force-only manifests are recorded under
`results/validation/`.

For cluster transfer, `run/compact_wuzhen_bec_outputs.py` creates a small archive
containing only the structures, PYATB polarization outputs, response manifest,
final energies, and final force blocks. It is compatible with Wuzhen's system
Python 3.6 and avoids copying wavefunctions or iteration-level SCF logs.

## Dependencies and validation levels

* Level 1 (included): ZStar, NumPy and the existing qNEP-format parser. It
  checks sparse labels, tensor shape, frame IDs, provenance, round-trip export,
  and manifest consistency. No DFT or GPU is needed.
* Level 2 (included small-model result): a cubic-only 83/21 split was trained
  with GPUMD 5.7 `charge_mode 1` and sparse `bec:R:9` labels. The held-out
  BEC metrics are recorded in
  `results/qnep_training/cubic_104_seed20260913/metrics.json`; GPUMD
  `compute_phonon` and the GPUMD force/BEC dumps feed the trained-model
  Phonopy NAC overlay in `results/figures/`. This is a compatibility benchmark,
  not production accuracy. The official qNEP model/data remain useful for an
  optional independent smoke test and are available from
  [Zenodo 10.5281/zenodo.18335947](https://doi.org/10.5281/zenodo.18335947),
  but are not copied into this repository.
* Level 3 (not included): GPU GPUMD MD plus Phonopy/DYNASOR post-processing is
  needed for temperature-dependent lattice constants, polarization, static
  and frequency-dependent dielectric response, P--E loops, or Figure 5/6
  style results. ZStar prepares reference data but does not train qNEP, run
  GPUMD MD, or replace Phonopy/DYNASOR.

The published qNEP BTO setup mixes r2SCAN energy/force/virial data with PBEsol
DFPT BECs. This example intentionally does not claim that exact reference
setup; any independent ABACUS/PBEsol result must be labelled as a ZStar
reference-data compatibility example.
