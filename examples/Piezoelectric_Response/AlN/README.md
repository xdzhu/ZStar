# Wurtzite AlN piezoelectric response

This is the primary PBE benchmark for ZStar's bulk strain-response workflow.
The polar axis is Cartesian `z`.  The ABACUS + PYATB route uses SG15/Dojo
norm-conserving pseudopotentials, 8-au numerical orbitals, 100 Ry, an `8x8x6`
mesh, `scf_thr=1e-8`, and a fixed-cell force threshold of `1e-4 eV/Angstrom`.
The 13-stage central ensemble samples `+-0.5%` engineering strain.

| Source | Method | `e31` | `e33` | `e15` (C/m2) | `d31` | `d33` | `abs(d15)` (pm/V) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ZStar / ABACUS + PYATB | PBE | -0.5690 | 1.3880 | -0.2973 | -2.068 | 4.975 | 2.628 |
| ZStar / native VASP | PBE | -0.5815 | 1.4614 | -0.3095 | -2.190 | 5.324 | 2.768 |
| de Jong et al. / VASP | PBE | -0.5801 | 1.4612 | -0.2893 | not reported | not reported | not reported |
| Bernardini and Fiorentini / VASP | GGA | not reported | not reported | not reported | -2.1 | 5.4 | 2.9 |
| Guy et al. / interferometry | experiment | not reported | not reported | not reported | -2.8* | 5.6 +/- 0.2 | not reported |
| Muensit et al. / interferometry | experiment | not reported | not reported | not reported | not reported | not reported | 3.6 +/- 0.2 |

References: [de Jong et al.](https://doi.org/10.1038/sdata.2015.53),
[Bernardini and Fiorentini](https://doi.org/10.1063/1.1482796),
[Guy et al.](https://doi.org/10.1063/1.125560), and
[Muensit et al.](https://doi.org/10.1063/1.125508). The asterisk marks the
`d31=-d33/2` value inferred in the extensional experiment. `|d15|` is used
because the cited calculations and measurements adopt different basal-axis
sign conventions. The full ZStar tensors and diagnostics are retained in
`results/`; no `d` value is reconstructed from an unrelated elastic dataset.

```bash
./run.sh check
./run.sh prepare
./run.sh run
./run.sh status
./run.sh collect
```

`run` executes the ABACUS + PYATB route directly inside the current allocation.
Set the executable and MPI environment variables described in the parent
README before using it on a cluster.  Completed markers make the calculation
restartable.  Redistributable inputs for the independent native VASP route are
retained in `run/vasp/`; see its README for the licensed `POTCAR` step.
