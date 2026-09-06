# Carbon dioxide (CO2)

This isolated-molecule PBE case is a second IR/Raman benchmark with a linear,
centrosymmetric structure. The inputs are ready for an ABACUS + PYATB `dim=0`
workflow; compact reference spectra and a benchmark figure are retained under
`results/`.

## One-command reproduction

Run `bash run.sh --dry-run` first, then
`ABACUS_COMMAND="mpirun -np 20 abacus" PYATB_COMMAND="pyatb" bash run.sh`.
The clean inputs and ABACUS assets are under `run/`; generated output is
written to `work/`.

```bash
mkdir -p work
cp -r run/. work/
cd work
zstar bec pre --stru STRU --input INPUT --pp assets --orb assets --dim 0 \
  --method central --displacement 0.01
zstar bec job --system shell
zstar bec run --root . --dim 0 --abacus-command "mpirun -np 20 abacus"
zstar bec post --root .
zstar phonon pre --stru STRU --dim 0
zstar phonon post --stru STRU --physical-dim 0
```

Molecular spectra must be interpreted with molecular activity units and are not
bulk dielectric functions.
