# qNEP training-data bridge

GPUMD qNEP is a charge-aware NEP4 model with long-range electrostatics. Target
atomic charges are **not required**. Its ordinary training labels remain total
energy, atomic forces, and optional virial/stress. Per-atom Born effective
charges are an optional additional target written as `bec:R:9` in extended XYZ.

This is a natural interface for ZStar, but BEC is not a substitute for the
energy/force/virial dataset. ZStar augments an existing NEP dataset and audits
the join.

## One labeled frame

```bash
zstar data qnep augment \
  --input train.xyz \
  --bec BEC.raw.dat \
  --frame 0 \
  --output train_qnep.xyz

zstar data qnep check --input train_qnep.xyz
zstar data qnep init --input train_qnep.xyz --output nep.in \
  --charge-mode 2 --lambda-z 0.5
```

`--bec` accepts `BEC.raw.dat`, Phonopy `BORN`, CP2K `cp2k_bec.json`, or VASP
`vasp_bec.json`.

## Multiple or partially labeled frames

GPUMD explicitly permits BEC labels for only some structures. Use a zero-based
CSV map:

```csv
frame,bec
0,labels/frame-0000/vasp_bec.json
25,labels/frame-0025/BEC.raw.dat
80,labels/frame-0080/cp2k_bec.json
```

```bash
zstar data qnep augment --input train.xyz --map bec_map.csv --output train_qnep.xyz
```

The generated audit JSON records every labeled frame, BEC source, atom count,
tensor conversion, and acoustic-sum residual. Atom labels and order are checked
when the BEC source contains species metadata.

BEC labels are written with ten digits after the decimal point. Canonical
`Z-BORN-*.out` files use eight digits, while JSON response records retain the
available floating-point precision. These are storage guarantees, not claims
of physical accuracy; convergence with respect to SCF thresholds, displacement
size, basis, and sampling remains mandatory.

## Exporting a sparse-BEC SCF campaign

Each SCF calculation generated for a finite-difference BEC workflow has a
real energy and force label.  It can therefore remain in a force-field dataset
even though only the neutral, undisplaced parent configuration has a BEC.
ZStar exports this pattern without inventing zero BEC matrices:

```bash
zstar data qnep export \
  --input bec_force_only_raw.jsonl \
  --annotations all_bec_annotated.jsonl \
  --output multiphase_pbesol_raw.xyz
```

`--annotations` is keyed by the parent `frame_id`.  ZStar inherits the parent
phase label for its displaced SCF children and attaches the BEC only to a
child named `PARENT::0.no-move`.  It position-matches atoms under periodic
boundary conditions before reordering the tensor, so a different ABACUS and
extxyz atom order cannot silently corrupt an oxygen-site BEC label.  The audit
records the explicit labeled/unlabeled counts and leaves energy and force
values unchanged.

For a controlled multiphase diagnostic, retain a fixed cubic benchmark and
append only selected phase-labelled frames:

```bash
zstar data qnep compose \
  --base cubic_full.xyz \
  --addition multiphase_pbesol_raw.xyz \
  --phases tetragonal orthorhombic rhombohedral \
  --max-per-phase 108 --seed 20260915 \
  --output cubic_plus_balanced_phases.xyz
```

The selection is deterministic, de-duplicates `frame_id`, preserves every
selected extxyz record byte-for-byte, and writes an audit.  If `cubic_full.xyz`
is used both in training and as a test file, its resulting errors are
**in-sample cubic fitting errors**, not a leakage-safe generalization metric.

After GPUMD finishes, score the generated `energy_test.out`, `force_test.out`,
and `bec_test.out` files with the exact BEC mask from the test set:

```bash
zstar data qnep score --test cubic_full.xyz --directory qnep_run
```

The BEC MAE/RMSE excludes qNEP's zero placeholders for unlabelled atoms; only
the frames whose extxyz schema explicitly contains `bec:R:9` contribute.

## Tensor convention and scientific limits

GPUMD stores the nine `bec:R:9` components in row-major order with electric
field/polarization as rows and force/displacement as columns, consistent with
the electric-force implementation `F_j = sum_i E_i Z_ij`. ZStar's canonical
files use displacement rows and polarization columns, so the exporter performs
an explicit transpose. Bypassing this conversion can silently swap off-diagonal
components.

qNEP assumes one constant high-frequency dielectric constant across a training
dataset when BEC supervision is enabled. The official documentation therefore
warns that BEC training usually applies to one material in one phase. Do not mix
chemistries, phases, inconsistent DFT settings, atom orders, polarization
branches, or incompatible dielectric screening in one BEC-supervised model.

Accordingly, a multi-phase BaTiO3 run is a compatibility and coverage
diagnostic, not a replacement for a phase-specific production qNEP model.  Its
energy, force, and BEC labels must come from declared calculations (for
example, one PBEsol pseudopotential/orbital/basis family); public reference
labels calculated with a different functional must not be silently mixed in.

All qNEP structures are treated as periodic in all directions. Molecular and 2D
data therefore require a deliberate periodic-cell and cutoff strategy.

Primary sources: [GPUMD `train.xyz` specification](https://gpumd.org/nep/input_files/train_test_xyz.html),
[`charge_mode`](https://gpumd.org/nep/input_parameters/charge_mode.html),
[`lambda_z`](https://gpumd.org/nep/input_parameters/lambda_z.html), and
[qNEP paper, DOI 10.1021/acs.jctc.6c00146](https://doi.org/10.1021/acs.jctc.6c00146).
