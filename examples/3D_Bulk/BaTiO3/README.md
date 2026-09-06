# Tetragonal BaTiO3

This PBEsol $P4mm$ bulk case demonstrates the standard three-dimensional BEC,
phonon, IR, and dielectric workflow. The compact reference directory includes
the insulating-state gate, BORN tensors, symmetry report, and response data.

## One-command reproduction

Run `bash run.sh --dry-run` first, then
`ABACUS_COMMAND="mpirun -np 20 abacus" PYATB_COMMAND="pyatb" bash run.sh`.
Generated stages go to `work/`; `run/` contains only the reproducible inputs.

```bash
cp -r run work
cd work
zstar bec pre --stru STRU --input INPUT --pp assets --orb assets --dim 3 \
  --method central --displacement 0.01
zstar bec job --system shell
zstar bec run --root . --dim 3 --abacus-command "mpirun -np 20 abacus"
zstar bec stat --root .
zstar bec post --root .
```

Then use `zstar phonon pre`, `zstar phonon post`, and `zstar spectra ir` for phonon-assisted IR, or
`zstar dielectric static/freq` for the electronic and lattice response. The
reference input is a validation snapshot; relax the structure and reconverge
the response before using it for production science.
