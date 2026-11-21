# Sb₂S₃ spectra in Figure 10

The VASP IR curve in panel (h) uses the [ten finite-displacement
Born tensors](../../sb2s3_vasp_fd/results/BEC_all_atoms.csv) and the
frequencies, masses and eigenvectors in `vasp_gamma_modes.json`. The
phonons come from the [VASP response calculation](vasp_response/).

Rebuild the curve from this directory in a Python environment with ZStar:

```bash
python rebuild_vasp_ir.py --output vasp_ir_rebuilt.dat
```

The reconstruction contracts each Born tensor with the mass-weighted
phonon displacement, squares the three Cartesian mode charges and
applies an 8 cm⁻¹ Lorentzian full width at half maximum. The last
column is the sum of the three components. Figure 10(h) divides
that column by its peak. The reconstruction uses the archived data and
requires no VASP executable or SCF calculation.
