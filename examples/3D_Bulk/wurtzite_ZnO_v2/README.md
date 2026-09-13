# Wurtzite ZnO — ZStar v2 piezoelectric gate

This is a 3D bulk validation case for the v2 homogeneous-strain response
ensemble.  The input uses the crystallographic hexagonal cell (4 atoms,
equivalent to the 2-atom primitive wurtzite basis) with `z || [0001]`.

The calculation is research-only until the rank/residual, branch matching,
mechanical-stability, and literature-comparison gates are all passed.  Each
geometry is evaluated by one ABACUS run followed by one PYATB polarization run;
that single PYATB run emits the three Cartesian polarization components.

Reference settings: PBEsol, Dojo-NC-FR 8-au LCAO orbitals, 100 Ry, `8x8x6`
k-mesh, `scf_thr=1e-8`, engineering-Voigt strain amplitude `1e-3`.

The large `run/` and `results/` trees are generated outside the repository
scratch area.  Pseudopotentials and orbitals are copied into private run
directories and are not committed.
