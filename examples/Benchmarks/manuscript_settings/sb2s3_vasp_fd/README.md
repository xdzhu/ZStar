# Sb₂S₃ Born effective charges from VASP finite displacements

`run/POSCAR` is the VASP-relaxed reference. `KPOINTS` and `INCAR`
record the 1 × 1 × 12 grid, 520 eV cutoff, PBE-D3(BJ), and the dipole
evaluation settings. The Born charges use the differences in total
dipole at the positive and negative endpoints of 12 vibrational modes,
evaluated from the stored electronic states of those endpoints.
Inversion, mirror symmetry, and the acoustic sum rule relate the
mode derivatives to the site tensors.

`results/BEC_all_atoms.csv` contains the full tensors in e for all ten
atoms, with rows for atomic displacement and columns for polarization.
The manuscript table shows the diagonal elements of the five inequivalent
sites. A separate Cartesian displacement gives S(1) Zxx of −0.522 e on
the same mesh, compared with −0.525497 e in the mode reconstruction.

The VASP PAW datasets are S and Sb, in POSCAR order. Assemble the POTCAR from your licensed installation. The dipole step reads the saved electronic state for each displacement.

[Figure 10 spectra and method notes](../fig10/).
