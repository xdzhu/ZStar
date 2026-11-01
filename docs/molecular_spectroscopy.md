# Molecular IR and Raman spectroscopy

The ABACUS route reuses the [Unified displacement workflow](unified_spectroscopy.md)
for APT, Gamma modes, IR and Raman. Its molecular position-matrix APT is
experimental and currently restricted to neutral, nonmagnetic closed-shell
molecules with Gamma-only sampling. An APT sum-rule pass is not an independent
accuracy or vacuum-convergence certificate.

## Scope and convention

The molecule is placed in a cell with enough vacuum to remove interactions
between periodic images. ZStar uses mass-weighted Gamma normal coordinates
`Q` in `angstrom * sqrt(amu)`. Molecular IR uses dipole derivatives obtained
from the APT; it is not obtained from a periodic Berry-polarization branch.
For Raman, `dalpha/dQ = V/(4*pi) * d(epsilon_r)/dQ` converts the dilute-cell
dielectric derivative to a molecular polarizability derivative.

The displayed spectra are normalized. The CSV files preserve dipole and
polarizability derivatives, but ZStar does not label the normalized curves as
gas-phase integrated cross sections.

## Calculation chain

Relax the molecule in a sufficiently large fixed cell and release all atoms
for the response calculations. Prepare, run and inspect the common ensemble:

```bash
zstar bec pre --stru STRU --dim 0
zstar bec run
zstar bec post
zstar phonon inspect --dim 0 --qpoints qpoints.yaml --json gamma_review.json
zstar spectra pre --response . --root spectra
zstar spectra run --root spectra
zstar spectra post --root spectra
```

The legacy normal-mode Raman-only workflow remains available, but its old
Berry-phase molecular IR route is disabled. Historical molecular IR results
without compatible APT provenance should be treated as unverified. See the
[diagnostics guide](workflow_diagnostics.md) before reusing old SCF results.

## Outputs

| Path | Contents |
| --- | --- |
| `BEC.raw.dat`, `BEC.dat` | Unprojected and projected atomic polar tensors. |
| `.zstar/molecular_apt_diagnostic.json` | Raw APT sum and projection diagnostics. |
| `.zstar/molecular_apt_validation.json` | Method, checks and source/output fingerprints. |
| `spectra/ir/ir_modes.csv` | Frequencies, dipole derivatives and IR activities. |
| `spectra/raman/raman_modes.csv` | Frequencies, Placzek activities and Raman tensors. |
| `spectra/spectra_result.json` | Response method, mode selection and spectrum settings. |

## Required convergence checks

- Optimize until forces and molecular geometry are stable.
- Confirm the vibrational subspace has no significant imaginary frequencies.
- Increase the vacuum size until converted `dmu/dQ` and `dalpha/dQ` are stable.
- Check the normal-coordinate amplitude, normally around
  `0.01-0.03 angstrom * sqrt(amu)`, for central-difference linearity.
- Converge the LCAO basis, cutoff, and PYATB response grid.
- Preserve molecular symmetry tightly enough that forbidden activities and
  degenerate mode splittings remain close to numerical zero.

## Historical Benchmarks

The frequency and selection-rule comparisons below describe historical
calculations. Their old Berry-derived molecular IR intensities have not been
validated by the experimental position-matrix route and must not be treated
as an accuracy certificate for the current molecular APT.

Methane is the primary non-centrosymmetric benchmark. The ABACUS/PBE harmonic
frequencies are 1287.93, 1516.62, 2968.29, and 3088.05 cm-1, within
1.13%-2.29% of the NIST fundamentals. The computed representation is
`A1 + E + 2 T2`: all fundamentals are Raman active, while only the two `T2`
families are IR active. Reference frequencies and assignments are from the
[NIST Chemistry WebBook](https://webbook.nist.gov/cgi/cbook.cgi?ID=C74828&Mask=887);
an independent theoretical comparison is available in
[PCCP 2016, DOI 10.1039/C6CP03463B](https://doi.org/10.1039/C6CP03463B).

Carbon dioxide is the complementary centrosymmetric benchmark. A direct
20-core run on a dedicated compute node used ABACUS 3.10.0 LTS, PBE, a 100 Ry cutoff, a
20 Angstrom cell, and no empirical frequency scaling. The accepted linear
geometry has a 1.17042 Angstrom C-O bond and a maximum residual force of
0.00623 eV/Angstrom. The reference band gap along the high-symmetry path is 8.618 eV.

| Fundamental | Symmetry | ZStar/ABACUS (cm-1) | NIST (cm-1) | Error | IR | Raman |
| --- | --- | ---: | ---: | ---: | --- | --- |
| bend (doubly degenerate) | Eu | 635.64 | 667 | -4.70% | active | inactive |
| symmetric stretch | A1g | 1331.99 | 1333 | -0.08% | inactive | active |
| asymmetric stretch | A2u | 2381.04 | 2349 | +1.36% | active | inactive |

Forbidden Raman activities are below `2.5e-15` of the strongest line, and the
forbidden IR activity is numerically zero. Thus the calculation recovers both
the bending degeneracy and the centrosymmetric mutual-exclusion rule. The
symmetric-stretch experimental Raman region is affected by Fermi resonance,
so the unperturbed fundamental is the appropriate harmonic comparison.
Experimental data are from the
[NIST CCCBDB](https://cccbdb.nist.gov/exp2x.asp?casno=124389&charge=0).

Together, CH4 and CO2 test both non-centrosymmetric activity and the strict
centrosymmetric mutual-exclusion rule. The overview below combines frequency
agreement, signed errors, allowed activities, and the calculated spectra in a
single traceable figure.

![Molecular IR and Raman validation overview](paper_figures/molecular_validation_overview.png)
