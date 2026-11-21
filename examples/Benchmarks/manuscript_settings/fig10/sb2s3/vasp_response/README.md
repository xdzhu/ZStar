# Sb₂S₃ VASP inputs for Figure 10

These inputs use the VASP-relaxed structure, PBE-D3(BJ), a 520 eV cutoff and
a Γ-centered 1 × 1 × 12 mesh. `IBRION = 5` evaluates the Γ-point phonons
by finite differences. `LEPSILON = .TRUE.` supplies the electric response
used for the archived IR curve. The Raman calculation uses displacements
along the resulting modes.

Use the `S` and `Sb` PAW-PBE datasets, in POSCAR order, from your licensed
VASP installation. The [finite-displacement BEC table](../../../sb2s3_vasp_fd/)
uses a separate polarization step on the same relaxed geometry.
