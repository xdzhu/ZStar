# Wurtzite ZnO piezoelectric response

ZnO provides a second PBE benchmark with the polar axis along Cartesian `z`.
The ABACUS + PYATB route uses the included norm-conserving pseudopotentials and
8-au numerical orbitals, 100 Ry, an `8x8x6` mesh, `scf_thr=1e-8`, and a
`1e-4 eV/Angstrom` fixed-cell force threshold.  The central ensemble contains
one reference and 12 `+-0.5%` engineering-strain structures.

| Source | Method | `e31` | `e33` | `e15` (C/m2) | `d31` | `d33` | `d15` (pm/V) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ZStar / ABACUS + PYATB | PBE | -0.5217 | 1.0475 | -0.3840 | -4.669 | 9.666 | -9.217 |
| ZStar / native VASP | PBE | -0.5369 | 1.0421 | -0.3993 | -4.887 | 9.750 | -10.828 |
| de Jong et al. / VASP | PBE | -0.5375 | 1.0368 | -0.3850 | not reported | not reported | not reported |
| Catti et al. / CRYSTAL | Hartree-Fock | -0.54 | 1.19 | -0.46 | -3.70 | 8.00 | -8.20 |
| Kobiakov / resonance | experiment | not reported | not reported | not reported | -5.12 | 12.3 | -8.3 |

References: [de Jong et al.](https://doi.org/10.1038/sdata.2015.53),
[Catti et al.](https://doi.org/10.1016/S0022-3697(03)00219-1), and
[Kobiakov](https://doi.org/10.1016/0038-1098(80)90502-5). The native VASP
archive uses the exact-hexagonal, symmetry-enabled result. Its internal-strain
decomposition warning is retained, but the independently closed total `e`,
positive-definite `C`, and algebraic `d=e C^-1` remain usable.

```bash
./run.sh check
./run.sh prepare
./run.sh run
./run.sh status
./run.sh collect
```

See the parent README for executable variables and scheduler boundaries.
`run.sh` reproduces the ABACUS + PYATB route.  Redistributable inputs for the
independent native VASP route are retained in `run/vasp/`; see its README for
the licensed `POTCAR` step.
