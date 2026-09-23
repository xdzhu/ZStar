# SiC BEC displacement convergence

This case scans `--displacement` over 0.005, 0.010, 0.015, 0.020, 0.025,
and 0.030 Angstrom using the packaged two-atom SiC input in `run/`.
Every point uses the Unified symmetry-adapted displacement ensemble and the
actual vectors written to `STRU` during response reconstruction.
The run keeps the insulating-state gate but skips the electronic dielectric
tensor because it is not required for a BEC convergence test.

```bash
bash run.sh
python analyze.py
```

On a PBS/Torque cluster, submit the same scan with:

```bash
bash run_pbs.sh
```

Set `ZSTAR_CONVERGENCE_ROOT` to place solver outputs elsewhere. Additional
arguments to `run.sh` are forwarded to `zstar bec run`; for example,
`bash run.sh --dry-run` prepares and inspects all six cases without launching
ABACUS or PYATB.

The analysis writes `results/SiC_displacement_convergence.csv` and matching
PDF/PNG plots. It reports the mean Si diagonal BEC and the largest tensor
change relative to the 0.010-Angstrom point.

## Retained result

The symmetry-projected Si response remains between `2.70024 e` and `2.70097 e`
over the full 0.005--0.030-Angstrom scan. The maximum component difference from
the 0.010-Angstrom result is `7.30e-4 e` (about `0.027%` of the BEC magnitude),
and the C tensor is equal and opposite. The JSON result retains every tensor at
eight-decimal precision.
