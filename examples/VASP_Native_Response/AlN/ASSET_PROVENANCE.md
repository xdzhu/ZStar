# Calculator Assets

Use licensed PBE PAW `Al/POTCAR` and `N/POTCAR` in POSCAR order.
POTCAR, WAVECAR, CHGCAR and VASP source are not redistributed.
The runner reads `$VASP_PSEUDO_ROOT/PBE/<element>/POTCAR` and retains SHA256
hashes of the actual stage inputs in `results/stage_input_sha256.txt`.

The initial wurtzite seed and supplied relaxed structure are included.
Compact native tensors, mode data and spectra are derived calculation outputs.
Rejected or interrupted runs stay in private scratch directories and are
excluded from the public result set. See the case README for numerical settings,
polarity, tensor conventions and reference locations.
