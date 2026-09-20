# Cubic BaTiO3: charge-aware ML force-field compatibility snapshot

This example documents a **ZStar-to-qNEP data-compatibility benchmark**, not a
production qNEP model or a reproduction of finite-temperature results from the
qNEP paper.  The companion ZStar commands prepare sparse Born-effective-charge
(BEC) labels, preserve unlabelled frames explicitly, and export qNEP extended
XYZ files.

The archived 100k-generation qNEP trials did not meet the intended cubic-BaTiO3
force target.  They are retained as an auditable negative result; do not use
their phonons, NAC, dielectric response, or polarization as CPC evidence.
See [`results/compatibility_snapshot/`](results/compatibility_snapshot/) for
the fixed-dataset metrics and decision record.

## Scope and prerequisites

ZStar needs only its ordinary Python dependencies for JSONL validation,
selection, and qNEP export.  ABACUS and PYATB are required to generate
first-principles BEC data.  GPUMD with qNEP is optional and required only to
train or run a qNEP model; Phonopy is required for a phonon calculation.

The intended workflow is:

1. Obtain E/F/(optional stress) frames from one declared DFT setup.
2. Select representative frames by temperature, phase, and geometry.
3. Run BEC only for the selected neutral parents; retain every finite-
   displacement SCF frame as an E/F sample without a BEC.
4. Export and validate qNEP extxyz with `zstar data qnep export` and
   `zstar data qnep check`.
5. Train and assess external qNEP/GPUMD software separately.

`run/run.sh` contains path-free command templates.  It intentionally does not
download data, submit DFT work, or start a GPU run.

## Scientific boundary

BEC is a response tensor, not a static partial charge, dipole, or polarization.
ZStar supplies the reference response data; qNEP learns dynamic charges and
GPUMD performs force-field evaluation.  Neither qNEP training nor GPUMD
molecular dynamics is implemented by ZStar.

No raw DFT directories, GPU models, large extxyz datasets, or caches are
stored in this repository.  Their source, calculation settings, and checksums
belong in a manifest outside Git.
