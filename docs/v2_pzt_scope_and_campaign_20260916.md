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

## Campaign checkpoint after the first complete ensembles

The following entries use one shared zero-strain geometry plus the twelve
`±0.005` engineering-strain geometries. Every geometry has one ABACUS stage and
one PYATB calculation that returns all three polarization components. Values are
raw finite-difference results in conventional Cartesian axes after an explicit
coordinate rotation where noted; a symmetry projection is diagnostic only.

| system | completed branch | proper `e` (C/m2) | `C` (GPa) | immediate audit |
|---|---|---|---|---|
| diamond Si | clamped + relaxed | `max|e|=5.33e-5` | relaxed `C11/C12/C44=174.46/68.05/85.47` | zero-piezo control passes the `1e-3 C/m2` absolute noise gate |
| 3C-SiC | clamped + relaxed | cubic-axis relaxed `e14/e25/e36=0.14245/0.14209/0.14246` | relaxed `C11/C12/C44=363.46/110.70/231.49` | rank complete; forbidden proper-e maximum `0.00506 C/m2`; internal-strain forbidden displacement `2.69e-4 Angstrom` |
| GaAs | clamped + relaxed | relaxed `e14/e25/e36=-0.263223/-0.263223/-0.263223` | relaxed `C11/C12/C44=102.79/43.78/52.14` | reproduces the earlier `-0.2627 C/m2` result; tensor symmetry residual `1.70e-5` |
| ZnO | clamped + relaxed review | clamped `e31=+0.3614`, `e33=-0.7398`, `e15=+0.3835`; relaxed `e31=-0.6132`, `e33=+1.2218`, `e15=-0.4620` | clamped `C11/C12/C13/C33/C44=277.0/96.2/71.9/288.1/57.5`; relaxed `211.0/123.7/110.5/210.3/40.4` | relaxed raw `d33=11.85 pm/V`, but its internal-strain symmetry gate fails; it is not a qualified material benchmark |

The 3C-SiC primitive-cell output is not cubic-axis-aligned. The reported cubic
numbers use the tested `rotate_piezoelectric_tensor` and
`rotate_elastic_tensor` coordinate transforms; the primitive raw matrices remain
unchanged in the response document. For the relaxed tensors, the corresponding
direct compliance conversion gives `d14=0.615/0.614/0.615 pm/V` for 3C-SiC and
`d14=-5.0486 pm/V` for GaAs.

As of this checkpoint, successful or preserved failed jobs have consumed
`135.3 core-h` (32 allocated CPUs times Slurm elapsed time); the later ZnO,
PbTiO3 and PZT work is tracked separately until it passes its gates. ZnO's
relaxed 13-geometry collection completed.  Its proper-piezo and elastic audits
pass, but the equal-weight acoustic-gauge internal-strain audit gives a forbidden
displacement of `4.24e-3 Angstrom`, above the fixed mixed-gate floor of
`1e-3 Angstrom`; the raw tensor is preserved for diagnosis and is explicitly not
symmetry-projected into a claimed benchmark.

PbTiO3 R1 restart 2 reached the explicit `Relaxation is converged!` marker at
`force_thr_ev=1e-4 eV/Angstrom` and `stress_thr=0.1 kbar`. Its final
`STRU_ION_D` was promoted into a dedicated R2r fixed-cell internal-relaxation
input, rather than reusing a `cell-relax` template: the generated input enforces
`calculation=relax`, `symmetry_prec=1e-3`, `scf_thr=1e-8` and
`relax_nmax=100`. HF job `27712477` is the R2r smoke test; no R3r ensemble will
be submitted unless it reaches the ionic convergence marker. Ordered PZT R1
stopped after 100 steps with stress converged but force still above the fixed
gate. Its original directory and log are retained; a new R1 restart from its
last `STRU_ION_D`, with unchanged production inputs, is HF job `27712478`.
Neither PbTiO3 nor PZT has a tensor result at this checkpoint.
