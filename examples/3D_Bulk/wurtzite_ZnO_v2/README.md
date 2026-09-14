# Wurtzite ZnO — ZStar v2 piezoelectric gate

This is a 3D bulk validation case for the v2 homogeneous-strain response
ensemble.  The input uses the crystallographic hexagonal cell (4 atoms,
equivalent to the 2-atom primitive wurtzite basis) with `z || [0001]`.

The calculation is research-only until the rank/residual, branch matching,
mechanical-stability, and literature-comparison gates are all passed.  Each
geometry is evaluated by one ABACUS run followed by one PYATB polarization run;
that single PYATB run emits the three Cartesian polarization components.

Reference settings: PBEsol, Dojo-NC-FR 8-au LCAO orbitals, 100 Ry, `8x8x6`
k-mesh, `scf_thr=1e-8`, engineering-Voigt strain amplitude `1e-3`.  The
reference structure was relaxed with `force_thr=1e-3 eV/Å`; the strained-ion
production audit used `force_thr=1e-4 eV/Å` because the looser threshold did not
reproduce the hexagonal shear-equivalent response.

Scheduler notes: on HF submit `tools/v2_piezo_hf.slurm` with Slurm (32 MPI
tasks, one OpenMP thread per task, no node exclusivity).  On 235 run
`tools/v2_piezo_235_direct.sh` inside the allocated compute node (40 MPI × 1
OMP); it does not submit PBS jobs.  The driver is resumable through its stage
markers, so do not start a second copy for the same case root.

The large `run/` and `results/` trees are generated outside the repository
scratch area.  Pseudopotentials and orbitals are copied into private run
directories and are not committed.
