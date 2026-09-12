# Finite-q phonon and NAC validation

## Scope

This record validates the v1 finite-q phonon extension after the pre-feature
freeze `zstar-v1-freeze-before-phonon-nac-20260912`. The test case is the fixed
cubic $Pm\bar{3}m$ BaTiO3 example, using the same PBEsol settings and BORN
archive as the Unified BEC case. It validates the workflow and output contract;
because the fixed cubic reference has an unstable mode, it is not used to claim
a stable static dielectric constant.

## Reproduction route

The archived validation calculation was run directly on the dedicated 235 nodes
with one MPI rank and 40 OpenMP threads per ABACUS process. This allocation was
used to validate the workflow, not as the recommended 3D production layout.
For a 3D bulk calculation, the recommended layout is normally
`OMP_NUM_THREADS=1` with the available cores assigned to MPI ranks. Three Phonopy symmetry-reduced
displacements were generated in a `2 2 2` supercell. The sequence was:

```text
zstar phonon pre --spectrum --supercell "2 2 2" --physical-dim 3
ABACUS force calculations for disp-001, disp-002, and disp-003
zstar phonon post --physical-dim 3
zstar phonon spectrum --nac --npoints 101 --mesh 20 20 20
```

The run completed with ABACUS 3.10.0-LTS, Phonopy 2.38.2, spglib 2.6.0, and
Seekpath 2.1.0. The finite-q calculation uses the BEC-generated `BORN` as a
regular copied file. No charge density or cube file is shared by symbolic link.

## Checks

- Phonopy generated the finite-q displacement set and collected all three force
  responses.
- `phonopy.yaml`, `FORCE_SETS`, `qpoints.yaml`, and `irreps.yaml` were written.
- spglib/Seekpath identified space group 221, `Pm-3m`, with the path labels
  Gamma--X--M--Gamma--R--X--R--M.
- The spectrum command wrote separate w/o NAC and with NAC band/DOS plots and
  a blue/red overlay plot, together with JSON metadata and PNG previews.
- The overlay draws the with-NAC curves after the w/o-NAC curves, so coincident
  branches remain visible.

The complete clean input, result archive, runner, and plots are retained in
`examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/`.
