# Native VASP validation

This compact archive records the native VASP cross-check used for the MoS2
spectroscopy comparison. The monolayer was relaxed and evaluated with VASP
6.3.2, PAW-PBE potentials, PBE+D3(BJ), a 600 eV plane-wave cutoff, a
33x33x1 k-point mesh, and an electronic convergence threshold of 1e-8 eV.

The optical frequencies are 283.626, 384.260, 406.272, and 469.712 cm^-1.
They differ by a mean absolute value of 2.542 cm^-1 from the matching
PBE+D3(BJ) values reported by Ulian and Valdre
(https://doi.org/10.1107/S1600576723002571).

Only compact, redistributable structure and post-processing products are
included. Licensed PAW datasets and large VASP restart files are omitted.
