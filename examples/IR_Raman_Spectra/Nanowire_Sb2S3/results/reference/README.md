# Public Reference Data

Gianfranco Ulian, DFT dataset on bulk and one-dimensional stibnite (Sb2S3),
version 1 (2026), DOI [10.17632/6tntvw37tr.1](https://doi.org/10.17632/6tntvw37tr.1).
Distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

`B3LYP-D3/` contains original downloaded CRYSTAL full-chain files, unmodified.
The original output identifies the damping as D3(BJ); the directory name
reflects the source archive's shorter label.
`extracted/` contains derived tables and the ZStar reference-mode audit.
The coordinate rotation used by the ZStar calculation is new (x,y,z) = old (y,z,x).
The original reference files retain their original axes and atom ordering.

The original IR curve uses column 1 (frequency) and column 3 (intensity);
the Raman curve uses columns 1 and 2 (isotropic total). Reference Raman
conditions are 298 K and 532 nm. No peak shift or intensity fitting is performed.
The figure normalizes each curve separately. The low-frequency rotation caveat
and differing XC/response approximations are described in the case README.

The original `RAMSPEC.DAT` also contains single-crystal directional Raman
intensities: columns 5-10 (one-based) are `xx`, `xy`, `xz`, `yy`, `yz`, `zz` in
the original CRYSTAL axes. Because ZStar (x,y,z) = CRYSTAL (y,z,x), ZStar's
wire-axis `zz` corresponds to CRYSTAL `xx` (column 5), and ZStar's crossed
`yz` corresponds to CRYSTAL `xz` (column 7). The powder total in column 2
must not be used as a directional reference. Reconstructing the deposited
sampled `RAMSPEC.DAT` from its listed mode frequencies and directional
intensities with ZStar's Lorentzian FWHM of 8 cm-1 reproduces the normalized
reference curve with mean absolute error below 1e-6. The same check passes
for `IRSPEC.DAT` using the original mode-charge vectors. Thus the reference's
8 cm-1 damping parameter matches the broadening used in these audits.

To redraw the comparison from the repository root:

```bash
python tools/shared_response/plot_sb2s3_comparison.py \
  examples/IR_Raman_Spectra/Nanowire_Sb2S3 --packaged
```
