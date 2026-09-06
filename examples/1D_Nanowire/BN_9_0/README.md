# BN(9,0) nanotube: BEC and zone-center phonons

The reference structure is centered in the transverse xy vacuum, with z periodic.
This PBE example obtains BEC and Gamma force constants from the same
Phonopy displacement ensemble. Periodic z uses PYATB Berry-phase response;
open x/y use charge-density dipoles.

`run/` contains clean inputs and included pseudopotentials/orbitals.
`results/` contains the existing numerical outputs and compact native evidence;
the hashes in `source_evidence.json` identify unchanged copies.
New calculations go to `work/`, never to the archived results.

```bash
bash run.sh --dry-run
bash run.sh --abacus-command "mpirun -np 40 abacus" --pyatb-command pyatb
```

Install ZStar and PYATB first. The external ABACUS executable is not bundled.
The default entry computes BEC and Gamma modes only; it does not repeat Raman jobs.
The complete spectroscopy case and its IR/Raman reproduction instructions remain
in [the spectroscopy directory](../../IR_Raman_Spectra/Nanotube_BN_9_0/README.md).
Existing Cartesian/Unified comparisons remain there as well.

## Independent VASP BEC calculation

The completed [comparison and native evidence](results/vasp_validation/README.md)
are included. Axial values agree within 0.3%; the remaining radial difference
is reported explicitly rather than hidden by normalization or projection.

The independent check uses the same relaxed geometry, PBE, PAW-PBE-54 B/N
potentials, a 500 eV cutoff, and a 1x1x12 Gamma-centered grid. It runs a
reference SCF followed by native DFPT (`LEPSILON`, including local fields).
It does not repeat structure optimization or compute additional phonons.

```bash
bash run_vasp.sh --dry-run
export VASP_POTENTIAL_DIR=/path/to/POT_GGA_PAW_PBE_54
export VASP_COMMAND="mpirun -np 40 vasp_std"
bash run_vasp.sh
```

The potential directory must contain `B/POTCAR` and `N/POTCAR`; licensed
VASP potentials are not distributed. New calculations use `work-vasp/` and
resume completed stages. The clean workflow preserves `--dim 1` metadata;
VASP still solves a three-dimensionally periodic vacuum supercell. No
isolated-tube transverse image correction is applied. Compare local radial,
tangential, and axial BEC components at identical coordinates, not a
vacuum-dependent dielectric tensor interpreted as an intrinsic wire value.
