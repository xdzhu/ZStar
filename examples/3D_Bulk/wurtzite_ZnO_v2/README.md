# Wurtzite ZnO — ZStar v2 piezoelectric gate

> **Archived conditional result, not a production template.** The calculation
> below truthfully records an early `0.1%`, `1e-6/1e-10` development run. New
> v2 inputs must use the fixed `±0.5%`, `force_thr_ev=1e-4 eV/Angstrom`,
> `scf_thr=1e-8`, `relax_nmax=100` protocol. ZnO remains unqualified because
> `e15/C44/internal-strain` and raw-residual gaps are unresolved.

This is a 3D bulk validation case for the v2 homogeneous-strain response
ensemble.  The input uses the crystallographic hexagonal cell (4 atoms,
equivalent to the 2-atom primitive wurtzite basis) with `z || [0001]`.

The calculation is research-only until the rank/residual, branch matching,
mechanical-stability, and literature-comparison gates are all passed.  Each
geometry is evaluated by one ABACUS run followed by one PYATB polarization run;
that single PYATB run emits the three Cartesian polarization components.

The accepted direct-response audit uses PBEsol, Dojo-NC-FR 8-au LCAO orbitals,
100 Ry, `8x8x6` k-mesh, engineering-Voigt strain amplitude `1e-3`,
`scf_thr=1e-10`, `force_thr=1e-6 eV/Å`, and `relax_nmax=100`.  Every v2
space-group operation uses `symprec=1e-3`; the equilibrium reference retains
backend symmetry while finite-strain stages set ABACUS `symmetry=0` so that a
real strain is never projected back onto the reference cell.  PYATB uses the
Zn/O Dojo valence setting `20 6`; one run returns all three Cartesian
polarizations.

The direct finite-difference piezoelectric and elastic tensors are accepted
for this case after projection onto the exact `P6_3mc` (`6mm`) response
subspace.  The independent proper components are
`e31=-0.61504`, `e33=1.26745`, and `e15=e24=-0.47714 C/m²`; the corresponding
`d31=-5.96`, `d33=12.46`, and `d15=-11.97 pm/V`.  The unprojected
internal-strain tensor retains a 1.50% symmetry diagnostic residual.  That is
reported rather than silently discarded, but it is not used to reject the
direct polarization--strain result or the derived `d=e(C^E)^{-1}` result.
It remains a separate validation target for the BEC--Lambda reconstruction.

Historical scheduler records name the 235 nodes on which this audit ran. All
future v2 calculations use HF Slurm with 32 MPI tasks, one OpenMP thread per task and no
node exclusivity. The driver is resumable through its stage markers, so do not
start a second copy for the same case root.

The large `run/` and `results/` trees are generated outside the repository
scratch area.  Pseudopotentials and orbitals are copied into private run
directories and are not committed.

The archived values above are not the current quantitative benchmark record.
The amended campaign result, its internal-strain reconstruction diagnostic, and
the standalone `d33` comparison are in
[the v2 piezoelectric case matrix](../../../docs/v2_piezoelectric_case_matrix.md).
