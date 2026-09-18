# Validation results

Computed on hf with VASP 6.3.2, PBE PAW, ENCUT=600 eV, Gamma 8x8x8,
EDIFF=1e-8, 64 MPI x 1 OMP, NCORE=4 and ISYM=0.
Native DFPT and finite-difference optical modes agree within 0.05 cm-1.
The native DFPT dielectric reconstruction closes within 4e-5 absolute;
epsilon-infinity is approximately 7.149 and the total is approximately 10.506.
The Raman optical triplet has mutually consistent activity and depolarization
ratios near 0.75. The IR-only cache test needs no additional VASP call.

The DFPT internal-strain tensor retains a force-balance warning. Use the
separately quality-checked native finite-difference elastic route for derived d;
do not interpret good optical-mode agreement as validation of every DFPT
electromechanical tensor. Sources and warnings are retained in the JSON records.

Mode IDs in the exported qpoints and Raman JSON use ascending frequencies.
Reuse `spectra_results.json` together with `qpoints.yaml`, not a subset NPY
without its mode IDs. Primitive-cell Gamma force constants are not a full
phonon-dispersion dataset.
POTCAR, WAVECAR and CHGCAR are excluded from the public case.
