# VESTA screenshot inputs

These VASP5 files were exported from the exact ABACUS `STRU` inputs retained
for the manuscript. Run `python ../export_vesta_structures.py` to regenerate
them and `python validate_vesta_structures.py` to verify atom counts, cells,
and fractional coordinates with ASE.

Suggested VESTA display ranges:

| Manuscript use | File | Suggested display |
|---|---|---|
| Spectroscopy, molecule | `CH4_molecule.vasp` | one molecule; hide the cell frame |
| Historical GaAs validation | `GaAs_nanowire.vasp` | 1 x 1 x 3 cells; not used in the current manuscript composite |
| Spectroscopy, slab | `MoS2_monolayer.vasp` | 4 x 4 x 1 cells; oblique view showing the S-Mo-S trilayer |
| Spectroscopy, bulk | `HfO2_tetragonal.vasp` | 2 x 2 x 2 cells; show the tetragonal cell and Hf-O coordination |
| Bulk BEC (a) | `BaTiO3_cubic.vasp` | 2 x 2 x 2 cells; show one central unit cell |
| Bulk BEC (b) | `HfO2_tetragonal.vasp` | 2 x 2 x 2 cells; show one central unit cell |
| 2D BEC (a) | `hBN_monolayer.vasp` | 5 x 5 x 1 cells; near-top oblique view |
| 2D BEC (b) | `alpha-In2Se3_monolayer.vasp` | 4 x 4 x 1 cells; oblique view exposing the quintuple layer |
| Molecular APT (a) | `H2O_molecule.vasp` | one molecule; hide the cell frame |
| Molecular APT (b) | `CH4_molecule.vasp` | one molecule; hide the cell frame |

The current one-dimensional BEC structures are also supplied in
`examples/1D_Nanowire/BN_9_0/run/structure.vasp` and
`examples/1D_Nanowire/Sb2S3/run/structure.vasp` (paths from the repository root).
Sb2S3, not the historical GaAs wire, occupies the current spectroscopy row.

For consistent manuscript panels, use a white background, orthographic
projection, the same atom-radius convention within each two-panel figure,
and export lossless PNG images at no less than 1800 px width. Do not add panel
letters in VESTA; the manuscript figure script will place them consistently.
