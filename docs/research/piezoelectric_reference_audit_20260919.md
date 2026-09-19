# Piezoelectric reference audit for wurtzite AlN and ZnO

This record documents the literature values used beside the public ZStar AlN
and ZnO examples. Only wurtzite-phase results are included. Stress coefficients
`e` use C/m2 and strain coefficients `d` use pm/V (= pC/N).

## AlN

| Source | Method | e31 | e33 | e15 | d31 | d33 | abs(d15) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| de Jong et al. (2015) | VASP/PBE | -0.5801 | 1.4612 | -0.2893 | - | - | - |
| Bernardini and Fiorentini (2002) | VASP/GGA, direct stress response | - | - | - | -2.1 | 5.4 | 2.9 |
| Guy et al. (1999) | interferometry | - | - | - | -2.8* | 5.6 +/- 0.2 | - |
| Muensit et al. (1999) | shear interferometry | - | - | - | - | - | 3.6 +/- 0.2 |

The Bernardini and Fiorentini paper writes the transverse coefficient as
`d13`; it is `d31` after transposing to the 3x6 convention used by ZStar. The
asterisk marks the `d31=-d33/2` estimate used in the extensional experiment.
The AlN shear comparison uses magnitudes because the sources do not share a
single basal-axis and shear-sign convention.

## ZnO

| Source | Method | e31 | e33 | e15 | d31 | d33 | d15 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| de Jong et al. (2015) | VASP/PBE | -0.5375 | 1.0368 | -0.3850 | - | - | - |
| Catti et al. (2003) | CRYSTAL/Hartree-Fock | -0.54 | 1.19 | -0.46 | -3.70 | 8.00 | -8.20 |
| Kobiakov (1980) | single-crystal resonance | - | - | - | -5.12 | 12.3 | -8.3 |

## Verified references

- M. de Jong et al., *Scientific Data* **2**, 150053 (2015),
  [doi:10.1038/sdata.2015.53](https://doi.org/10.1038/sdata.2015.53).
- F. Bernardini and V. Fiorentini, *Applied Physics Letters* **80**,
  4145-4147 (2002),
  [doi:10.1063/1.1482796](https://doi.org/10.1063/1.1482796).
- I. L. Guy, S. Muensit, and E. M. Goldys, *Applied Physics Letters* **75**,
  4133-4135 (1999),
  [doi:10.1063/1.125560](https://doi.org/10.1063/1.125560).
- S. Muensit, E. M. Goldys, and I. L. Guy, *Applied Physics Letters* **75**,
  3965-3967 (1999),
  [doi:10.1063/1.125508](https://doi.org/10.1063/1.125508).
- M. Catti, Y. Noel, and R. Dovesi, *Journal of Physics and Chemistry of
  Solids* **64**, 2183-2190 (2003),
  [doi:10.1016/S0022-3697(03)00219-1](https://doi.org/10.1016/S0022-3697(03)00219-1).
- I. B. Kobiakov, *Solid State Communications* **35**, 305-310 (1980),
  [doi:10.1016/0038-1098(80)90502-5](https://doi.org/10.1016/0038-1098(80)90502-5).

The values are literature anchors, not identical-Hamiltonian validation data.
Pseudopotentials, basis sets, exchange-correlation approximations, optimized
structures, elastic boundary conditions, and axis conventions can all change
individual components.
