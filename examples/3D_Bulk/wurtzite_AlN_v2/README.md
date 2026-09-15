# Wurtzite AlN — ZStar v2 piezoelectric gate

This is a 3D bulk validation case for the v2 homogeneous-strain response
ensemble.  The input uses the crystallographic hexagonal cell (4 atoms,
equivalent to the 2-atom primitive wurtzite basis) with `z || [0001]`.

The calculation is research-only until the rank/residual, branch matching,
mechanical-stability, and literature-comparison gates are all passed.  Each
geometry is evaluated by one ABACUS run followed by one PYATB polarization run;
that single PYATB run emits the three Cartesian polarization components.

Reference settings: PBEsol, Dojo-NC-FR 8-au LCAO orbitals, 100 Ry, `8x8x6`
k-mesh, `scf_thr=1e-8`, engineering-Voigt strain amplitude `1e-3`.

The archived result was refreshed with a strained-stage force-convergence audit:
the 12 strained structures used `force_thr_ev=1e-5 eV/Angstrom` in HF Slurm job
`27682276` (node268, 32 MPI x 1 OMP), while the reference structure from job
`27678427` was retained and checked against the explicit `1e-3 eV/Angstrom`
reference equilibrium gate.  Every strained stage ended below `9.276e-6
eV/Angstrom` and was followed by one three-direction PYATB polarization run.

Scheduler notes: on HF submit `tools/v2_piezo_hf.slurm` with Slurm (32 MPI
tasks, one OpenMP thread per task, no node exclusivity).  On 235 run
`tools/v2_piezo_235_direct.sh` inside the allocated compute node (40 MPI × 1
OMP); it does not submit PBS jobs.  The driver is resumable through its stage
markers, so do not start a second copy for the same case root.

The preparation record uses ideal `P6_3mc` operations.  The collected reference
is audited with the same fixed v2 tolerance `symprec=1e-3` and is also
`P6_3mc`.  All v2 stages use this tolerance consistently.  The tighter
strained-stage audit reduces the internal-strain symmetry-projection residual
from about `3.19e-2` to `4.15e-4`, below the declared `1e-3` gate.  The raw
internal-displacement fit residual is still `2.59e-2`, so strain-amplitude
linearity and the literature comparison remain open; the result is therefore
still research-only.
