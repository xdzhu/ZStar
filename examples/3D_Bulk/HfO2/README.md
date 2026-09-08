# Tetragonal HfO2: BEC and dielectric response

The validated inputs use PBEsol, ONCV
pseudopotentials, Hf 6s3p3d2f1g and O 2s2p1d **9-bohr** orbitals,
100 Ry, a Gamma-centered 10x10x7 mesh, and SCF threshold 1e-8.
The six-atom P42/nmc structure has a=3.55652 and c=5.13487 Angstrom.

`run/` contains clean inputs and included PP/ORB assets. `results/` contains
the validated BEC, phonons, IR/Raman data and dielectric curves;
`provenance.json` identifies their settings. Historical 10-au inputs
and older tensors are preserved under `legacy/before_20260906/`.
They must not be substituted for the current reference.

## Run

Install the current ZStar package and PYATB, load your cluster environment,
and inspect the commands before executing:

```bash
bash run.sh --dry-run
ABACUS_COMMAND="mpirun -np 40 abacus" PYATB_COMMAND="pyatb" bash run.sh --stage all
```

Fresh output goes into `work/`, never `results/`. The default unified
ensemble uses four symmetry-adapted displacements plus one reference SCF.
The actual written displacement vectors determine the derivatives.

After completion, from `work/`:

```bash
zstar dielectric static
zstar dielectric freq --plot
```

The retained literature-comparison tensors use central 0.01-Angstrom
displacements. The unified rerun uses the 0.02-bohr default; its matched
accuracy and timing controls are in `3D_Bulk/t_HfO2/`. Small
finite-step differences are expected. Raman requires additional
polarizability derivatives: use `IR_Raman_Spectra/Bulk_HfO2/` for that
workflow. These Gamma modes do not demonstrate finite-wavevector
stability or LO-TO splitting.
