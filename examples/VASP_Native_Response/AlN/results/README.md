# Reference Results

Structural relaxation has converged. `AlN_relaxed.vasp` retains P6_3mc / 6mm,
with a=3.1280583 angstrom and c=5.0151373 angstrom in this PBE calculation.
Native response and mixed-route Raman are complete. `validation.json` checks
raw OUTCAR/XML consistency, dielectric closure, stable optical modes, 6mm
piezoelectricity and e=dC. `spectral_validation.json` checks the nine optical
mode IDs and 6mm IR/Raman selection rules; both pass.

Accepted native strain results: e31=-0.58162, e33=1.46150, e15=-0.30952 C/m2;
d31=-2.19017, d33=5.32440, d15=-2.76820 pm/V.
epsilon-infinity diagonal: 4.474795, 4.474795, 4.690378;
fixed-strain total dielectric diagonal: 8.229399, 8.229405, 9.747570.
Gamma optical DFPT/finite-difference frequencies differ by at most 0.133 cm-1.
Native DFPT internal-strain warnings remain in the records; derived d comes
from the quality-checked strain finite-difference route, not the warned DFPT tensor.

Raman and IR inactive-mode activities are below 5e-8 and 3e-7 respectively,
relative to their active maxima. The spectra are Gamma TO results without
directional NAC. They do not validate absolute experimental intensities.
Raman JSON and qpoints use matching ascending-frequency IDs.

Historical relaxation/DFPT EDIFF=1e-8; accepted elastic/Raman EDIFF=1e-9.
Actual stage hashes and Slurm accounting accompany the compact results.
Rejected/interrupted jobs in the accounting file are not additional valid datasets.
Licensed POTCAR, WAVECAR and CHGCAR files are not distributed.
