# Electrostatic-potential examples

These cases exercise `zstar pot` on two-dimensional electrostatic-potential
cubes. `MoS2` is a non-polar slab reference, `In2Se3` demonstrates the
out-of-plane polar-slab analysis, and `GeS` provides the strong in-plane-polar
comparison used in the paper. `SnS`, `SnSe`, and `SnTe` retain the broader
directional-potential family.

`GeS_nonpolar` supplies the matched fixed-ion, inversion-symmetric control,
including its native compressed cube and SCF evidence. `bash run.sh` regenerates
this reference offline; `bash run.sh --calculate` starts a fresh fixed-ion SCF.
It is not a verified saddle point. The paper uses a shared color scale for the
polar/nonpolar pair and tiles both maps 3x3 only when plotting.

Every case has the same delivery layout:

```text
case/
  run/       input contract (and ABACUS assets when distributed)
  results/   compact, verified reference outputs
  run.sh     one-command post-processing entry point
```

Run `bash run.sh --dry-run` first. A real run expects a converged ABACUS
electrostatic-potential cube, supplied with `--cube PATH` or `ZSTAR_CUBE`.
Outputs are written to the sibling `work/potential/` directory and never into
`run/` or `results/`.

The SnS-family cases intentionally distribute compact post-processing results
and the exact command contract, but not the original raw cube or the private
upstream SCF inputs. Their `run/README.md` records this boundary and the
source provenance. The retained profiles include the `a+b` and `a-b` lattice
directions, the z profile, and tiled planar maps.

See [`docs/potential_examples.md`](../../docs/potential_examples.md) for the
physical interpretation of the directional profiles and the 2D polarization
potential-difference workflow.
