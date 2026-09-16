# Zinc-blende GaAs — ZStar v2 piezoelectric gate

> **Archived method audit, not a production template.** This result used the
> earlier `0.1%` amplitude. New v2 production inputs use fixed `±0.5%`,
> `force_thr_ev=1e-4 eV/Angstrom`, `scf_thr=1e-8`, `relax_nmax=100` and HF
> Slurm. GaAs remains pending a definition- and functional-matched PBEsol/PBE
> theoretical `e14` anchor.

This is a 3D cubic validation case.  The conventional cubic cell (8 atoms) is
used so the Cartesian axes and the `F-43m` point group are explicit.  Its only
independent piezoelectric coefficient is the shear coefficient `e14` (with
symmetry-related copies), making it an audit of engineering shear and cubic
coordinate conventions rather than a second hexagonal `e33` test.

The calculation is research-only until the rank/residual, branch matching,
mechanical-stability, and literature-comparison gates are all passed.  Each
geometry is evaluated by one ABACUS run followed by one PYATB polarization run;
that single PYATB run emits the three Cartesian polarization components.

Reference settings: PBEsol, Dojo-NC-FR 8-au LCAO orbitals, 100 Ry, `8x8x8`
k-mesh, `scf_thr=1e-8`, engineering-Voigt strain amplitude `1e-3`.

Historical scheduler records are retained in provenance. Future v2 calculations use HF
Slurm with 32 MPI tasks, one OpenMP thread per task and no node exclusivity.
The driver is resumable through its stage markers, so do not start a second
copy for the same case root.
