# PZT scope and 3D production campaign (2026-09-16)

## PZT is a model family, not one crystal

`PZT` denotes the solid solution `Pb(Zr1-xTix)O3`; neither the composition nor
the crystal/B-site configuration is unique. Near the morphotropic phase boundary
(`x` approximately 0.48--0.50 in the Ti-fraction convention), tetragonal,
monoclinic and rhombohedral descriptions occur, and finite ordered supercells can
have different soft modes. A calculation must therefore state composition,
phase, B-site configuration, cell and temperature context before quoting `e` or
`d`.

The first ZStar model is deliberately narrow:

- composition: `PbZr0.5Ti0.5O3`;
- B-site order: alternating Ti/Zr layers along `[001]` (1:1 layered order);
- starting phase: polar tetragonal `P4mm`;
- cell: 10 atoms, `a=b=3.860784 Å`, `c=8.494565 Å` before PBEsol relaxation;
- functional/basis: PBEsol, Dojo-NC-FR pseudopotentials and 10-au DZP orbitals,
  100 Ry;
- reciprocal mesh: `9x9x4`, matched to the parent PbTiO3 `9x9x8` reciprocal
  density;
- structure audit: `P4mm` (No. 99) at `symprec=1e-3 Å`.

This model follows the explicit-ordering logic of
Sághi-Szabó, Cohen and Krakauer, Phys. Rev. B 59, 12771 (1999), DOI
`10.1103/PhysRevB.59.12771`. It is not claimed to represent disordered PZT,
`PbZr0.52Ti0.48O3` in its monoclinic `Cm` phase, or a configurational average.
Baker and Bowler, Phys. Rev. B 100, 224305 (2019), DOI
`10.1103/PhysRevB.100.224305`, explicitly show why different B-site orderings
must be studied separately.

## Submitted production R1 gates

All jobs use HF Slurm, one non-exclusive allocation with `32 MPI x 1 OMP` per
ABACUS calculation. Inputs enforce `symmetry_prec=1e-3`, `force_thr_ev=1e-4
eV/Å`, `stress_thr=0.1 kbar`, `scf_thr=1e-8`, and `relax_nmax=100`.

| system | intended structure | functional | R1 job | partition | status at submission |
|---|---|---|---:|---|---|
| wurtzite ZnO | `P6_3mc` | PBEsol | 27706955 | hfacnormal04 | submitted |
| 3C-SiC | `F-43m` | PBE | 27706956 | hfacnormal04 | submitted |
| zinc-blende GaAs | `F-43m` | PBEsol | 27706957 | hfacnormal04 | submitted |
| tetragonal PbTiO3 | `P4mm` | PBEsol | 27706958 | hfacnormal02 | submitted |
| ordered PZT50/50-[001] | `P4mm` | PBEsol | 27706959 | hfacnormal02 | submitted |
| diamond Si control | `Fd-3m` | PBE | 27707005 | hfacnormal04 | submitted |

The diamond-Si row corrects an earlier planning error: 3C-SiC is
non-centrosymmetric and may have `e14`; it cannot serve as a zero-piezoelectric
control. Only converged R1 `STRU_ION_D` files are promoted to fixed-cell R2r and
then to the `±0.5%` central-strain ensembles. No result in this document is a
completed tensor or a literature agreement claim.
