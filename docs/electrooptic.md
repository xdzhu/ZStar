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

## AlP comparison with ABINIT

For zincblende AlP, the same ABINIT inputs give r_yzx = -0.9535 pm/V
(electronic), +0.5361 pm/V (ionic), and -0.4174 pm/V (fixed-strain total).
The longitudinal phonon along [100] is at 534.69 cm^-1. Its yz Raman
susceptibility is 0.006864 in the ABINIT convention, versus 0.004315
if the macroscopic-field term is set to zero. The reference is the
[ABINIT nonlinear tutorial](https://docs.abinit.org/tutorial/nlo/) with the
matching tnlo_3.ddb.out and tnlo_4.abo. The header of the DDB specifies Al
and P.

## Electronic chi2 from finite-field dipoles

Supply a JSON object with field_step_V_m, directions (n Cartesian triples),
zero_C_m2, plus_C_m2, and minus_C_m2. Rows in the two last arrays are paired
clamped-ion polarizations for plus and minus the reference field multiplied
by the corresponding direction. Keep the same cell, electronic settings,
and polarization branch across the pairs. A direction such as [0,1,1]
applies the specified field step along both y and z. Six independent
quadratic directions are required.

    zstar dielectric chi2 --input paired_fields.json --output chi2.json

The command reports the largest symmetry and fit residuals. Repeat at
another field step to check truncation and SCF precision. The output is
accepted by zstar dielectric electrooptic --chi2. A check on the archived
AlAs dipoles gave chi_xyz = 30.4489 pm/V and agreed with the
[Materials Cloud tensor](https://archive.materialscloud.org/records/kqe32-5cy26)
to 0.0012 pm/V across all components.
