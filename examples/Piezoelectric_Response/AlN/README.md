# Wurtzite AlN piezoelectric response

This is the primary PBE benchmark for ZStar's bulk strain-response workflow.
The polar axis is Cartesian `z`.  The ABACUS + PYATB route uses SG15/Dojo
norm-conserving pseudopotentials, 8-au numerical orbitals, 100 Ry, an `8x8x6`
mesh, `scf_thr=1e-8`, and a fixed-cell force threshold of `1e-4 eV/Angstrom`.
The 13-stage central ensemble samples `+-0.5%` engineering strain.

| Source | `e31` | `e33` | `e15` (C/m2) | `d33` (pm/V) |
| --- | ---: | ---: | ---: | ---: |
| ZStar / ABACUS + PYATB | -0.5690 | 1.3880 | -0.2973 | 4.975 |
| ZStar / native VASP | -0.5815 | 1.4614 | -0.3095 | 5.324 |
| de Jong et al. / VASP-PBE | -0.5801 | 1.4612 | -0.2893 | not reported |

The external dataset is de Jong et al., *Scientific Data* **2**, 150053
(2015), DOI: [10.1038/sdata.2015.53](https://doi.org/10.1038/sdata.2015.53).
The full tensors and diagnostics are retained in `results/`; the table does not
compare `d` with a value reconstructed from an unrelated elastic dataset.

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
