# Molecular APT extraction and Gamma diagnostics

This is a compact **research validation record**, not a self-contained DFT
input set and not an independent accuracy certificate. It documents the
zero-dimensional ABACUS position-matrix APT and its checks after the historical
Berry-derived molecular IR issue was identified.

`results/CH4_HSE_DZP/` contains the unprojected CH4 APT and mode-resolved IR
and Raman outputs from replaying an existing neutral closed-shell HSE06/DZP
Gamma ensemble. All four geometries use the same original SCF data. The
reference Γ gap is 13.8032 eV; the reconstructed raw APT sum has a largest
diagonal magnitude of about 1.17e-5 e. The three rotational modes are at
approximately -24.27 cm-1, so rotational invariance still requires attention.
The nine internal modes are positive in this retained example.

The four original charge cubes were also integrated without density
normalization using a fixed molecular-center origin and independently
reconstructed with the same symmetry operations. The full raw APT differs from
the position-matrix result by at most 0.001361 e and by 1.042% in relative
Frobenius norm. These are two extraction routes from **the same SCF density**,
not independent DFT methods or evidence of converged basis/vacuum settings.
Raman uses PYATB's independent-particle static response, not a fully screened
local-field calculation. The benchmark does not validate all relative Raman
intensities. Large source matrices and charge cubes are not included.

For a new calculation, follow the [molecular guide](../../../docs/molecular_spectroscopy.md),
inspect `.zstar/molecular_apt_diagnostic.json` and the fingerprint receipt,
and perform independent checks appropriate to the molecule. Historical
Berry-derived molecular `BEC.dat` files are not accepted as verified IR inputs.
The automated regression tests cover the pre-projection guard, Gamma mode
classification and source changes:

```bash
python -m pytest tests/test_molecular_position.py tests/test_molecular_response_quality.py \
  tests/test_molecular_apt_validation.py tests/test_gamma_mode_assessment.py
```
