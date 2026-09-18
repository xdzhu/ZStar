# Calculator Assets

Use licensed PBE PAW `Si/POTCAR` and `C/POTCAR` in POSCAR order.
POTCAR, WAVECAR, CHGCAR and VASP source are not redistributed.
The runner reads `$VASP_PSEUDO_ROOT/PBE/<element>/POTCAR` and records actual
stage-input SHA256 hashes in `results/stage_input_sha256.txt`.

The cubic two-atom seed and relaxed structure are included. Compact tensors,
Gamma modes and spectra come from the completed hf VASP 6.3.2 calculations.
Native internal-strain warnings are retained in the records; failed preliminary
jobs are not validation results. See the case README for numerical settings.
