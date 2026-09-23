# Monolayer hBN BEC vacuum convergence

This case scans the out-of-plane cell length `Lz` over 15, 20, 30, and 40
Angstrom. The hBN layer remains at fractional `z = 0.5`; its in-plane lattice,
k-point density, pseudopotentials, and orbitals are held fixed using the
packaged input in `run/`.
The run keeps the insulating-state gate but skips the electronic dielectric
tensor because the scan targets BEC convergence.

```bash
bash run.sh
python analyze.py
```

On a PBS/Torque cluster, submit the same scan with:

```bash
bash run_pbs.sh
```

The scan compares the in-plane and out-of-plane BEC components rather than a
raw supercell dielectric constant, which contains the intentionally varied
vacuum volume. `results/hBN_vacuum_convergence.csv` and the PDF/PNG plot retain
the compact convergence record.

## Retained result

Across 15--40 Angstrom, the B in-plane response changes by only
`1.41e-5 e`. The out-of-plane response decreases from `0.36355 e` at 15
Angstrom to `0.33607 e` at 40 Angstrom; its 30-to-40-Angstrom change remains
`0.00520 e`. The scan therefore demonstrates that convergence must be assessed
component by component and does not label the 40-Angstrom out-of-plane value as
an exact infinite-vacuum limit. The JSON result retains all tensor components.
