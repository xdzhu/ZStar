# Static electronic chi2 in zincblende AlAs

This example uses the paired finite electric fields on a fixed-ion AlAs
cell from Bastonero and Marzari's open calculation archive. It extracts a
second derivative from the dipole response and compares it with the
authors' archived tensor.

    zstar dielectric chi2 --input fields.json --output chi2.json

The xyz component is 30.4489 pm/V. The largest absolute difference from
the archived tensor is 0.00119 pm/V. The field/dipole data, units and
node UUIDs identify the comparison. Both workflows use the same
finite-field SCF output.

The archive uses QE's Cartesian field in Rydberg atomic units and zeroed
electronic dipoles in the matching convention. The compact input gives
the converted V/m and C/m². The input is one field amplitude,
approximately 0.00909 V/Å on each nonzero Cartesian component. In the
original archive a second amplitude gives 30.4607 pm/V for xyz.

[Original Materials Cloud archive and reuse terms](https://archive.materialscloud.org/records/kqe32-5cy26)
