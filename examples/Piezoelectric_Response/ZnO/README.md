# Wurtzite ZnO piezoelectric response

ZnO provides a second PBE benchmark with the polar axis along Cartesian `z`.
The ABACUS + PYATB route uses the included norm-conserving pseudopotentials and
8-au numerical orbitals, 100 Ry, an `8x8x6` mesh, `scf_thr=1e-8`, and a
`1e-4 eV/Angstrom` fixed-cell force threshold.  The central ensemble contains
one reference and 12 `+-0.5%` engineering-strain structures.

| Source | `e31` | `e33` | `e15` (C/m2) | `d33` (pm/V) |
| --- | ---: | ---: | ---: | ---: |
| ZStar / ABACUS + PYATB | -0.5217 | 1.0475 | -0.3840 | 9.666 |
| ZStar / native VASP | -0.5369 | 1.0421 | -0.3993 | 9.750 |
| de Jong et al. / VASP-PBE | -0.5375 | 1.0368 | -0.3850 | not reported |

The external dataset is de Jong et al., *Scientific Data* **2**, 150053
(2015), DOI: [10.1038/sdata.2015.53](https://doi.org/10.1038/sdata.2015.53).
The native VASP archive uses the exact-hexagonal, symmetry-enabled result.  Its
internal-strain decomposition warning is retained, but the independently
closed total `e`, positive-definite `C`, and algebraic `d=e C^-1` remain usable.

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
