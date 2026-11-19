# Electro-optic response and longitudinal Raman

Run the postprocessor on matched Gamma transverse-optical modes, Born
effective charges, permittivity, and a bulk Raman mode table.

    zstar dielectric electrooptic \
      --qpoints qpoints.yaml --born BORN \
      --raman raman_spectrum/raman_modes.csv --output electrooptic.json

Raman columns must store derivatives of relative permittivity with respect
to the mass-weighted mode coordinate in 1/(angstrom sqrt(amu)). Mode IDs
and frequencies must match the complete Gamma optical subset. Use the
same phase convention and structure for both files. The output axes are
optical row, optical column and applied field. The ionic fixed-strain
term has units of pm/V.

Add the static electronic susceptibility with --chi2 chi2.json. The file
is a nested 3 x 3 x 3 array in pm/V, using P(2) = epsilon_0 chi2 E E.
This adds the clamped-ion electronic term and the total fixed-strain
tensor. With --direction x y z, the code also diagonalizes the directional
long-wavelength dynamical correction and applies the macroscopic field to
the Raman derivative. The program treats the direction as Cartesian.

Add both --photoelastic p.json and --piezoelectric d.json to calculate
the relaxed-stress result. The photoelastic array has shape 3 x 3 x 6
and describes the relaxed-ion inverse-permittivity derivative with respect
to engineering Voigt strain in order xx, yy, zz, yz, xz, xy. The
piezoelectric array has shape 6 x 3 in pm/V using the same strain order.

The method follows [Veithen et al. (2005), Eqs. 30 and 37–41 and Appendix A](https://doi.org/10.1103/PhysRevB.71.125107).

## AlN example

From the ZStar source root, use the archived native VASP AlN response.

    case=examples/VASP_Native_Response/AlN/results
    zstar dielectric electrooptic --qpoints "$case/qpoints.yaml" \
      --born "$case/dfpt/BORN" --raman "$case/raman_spectrum/raman_modes.csv" \
      --output aln-ionic-electrooptic.json

The fixed-strain ionic terms r_xxz, r_zzz, and r_xzx are approximately
-0.885, 1.699, and -0.575 pm/V on the supplied Cartesian axes. A separate
Cartesian harmonic calculation with the archived force constants gives
the same components to 0.001 pm/V.
