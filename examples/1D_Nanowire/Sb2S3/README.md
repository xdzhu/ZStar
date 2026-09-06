# Sb2S3 nanowire: BEC and zone-center phonons

The reference structure is centered in the transverse xy vacuum, with z periodic.
This PBE+D3(BJ) example obtains BEC and Gamma force constants from the same
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
in [the spectroscopy directory](../../IR_Raman_Spectra/Nanowire_Sb2S3/README.md).
Existing Cartesian/Unified comparisons remain there as well.
