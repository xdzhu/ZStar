# Spectra and Born charges used in the manuscript

The spectra and reference markers here are the data used in Figure 10.
`sources.sha256` checks their bytes against the figure build.

| Figure 10 | Input settings | Calculation and reference curves |
| --- | --- | --- |
| Tetragonal HfO₂ | [ABACUS](../../../3D_Bulk/t_HfO2/run/) and [VASP](../../../backend_examples/calculator_spectroscopy/vasp_hfo2/) | [Spectra](hfo2/). ABACUS and VASP use PBEsol and their own relaxed cells. The VASP PAW datasets are Hf_pv and O. Published markers are the Γ-point frequencies of [Phonix mp-1018721](https://phonix-db.org/ver2026.03.28/data_1018001-1019000/mp-1018721.html). |
| Monolayer MoS₂ | [Common Table 1 structure](../mos2_table1/) | [Spectra and mode data](mos2/). ABACUS and VASP use identical geometry and electronic sampling with PBE-D3(BJ). VASP uses Mo_sv and S PAW datasets. Gray markers are the frequencies in [Ulian and Valdrè, Table 3](https://doi.org/10.1107/S1600576723002571). The Raman panel sums the in-plane and mixed-polarization channels on the in-plane peak scale. |
| Isolated Sb₂S₃ chain | [ABACUS](../../../IR_Raman_Spectra/Nanowire_Sb2S3/) and [VASP response inputs](sb2s3/vasp_response/) | [Spectra](sb2s3/). The VASP PAW datasets are S and Sb, in POSCAR order. The plotted VASP IR uses the archived DFPT charges. The red crossed Raman spectrum uses the transverse local-field tensor. Gray spectra are from [Ulian's CRYSTAL dataset](https://data.mendeley.com/datasets/6tntvw37tr/1). |
| CH₄ | [ABACUS](../../../IR_Raman_Spectra/Molecule_CH4/) and [VASP](../ch4_vasp/) | [Spectra](ch4/). VASP uses C and H PAW datasets. Reference markers use the gas-phase VASP/PBE harmonic frequencies in [Yadavalli et al., Table S13](https://doi.org/10.1039/D1CP00862E). |

The main BEC tables use the [dimensional examples](../README.md).
The revised HfO₂ table compares [full tensors](hfo2/bec_tensor_comparison.json)
from ABACUS, VASP and Phonix. The Sb₂S₃ BEC table uses the [ten-atom VASP
finite-displacement tensors](../sb2s3_vasp_fd/results/BEC_all_atoms.csv).

Supply VASP PAW datasets through your own VASP installation. The
directories contain input settings, structures and response data.
