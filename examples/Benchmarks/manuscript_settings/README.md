# Manuscript calculation settings

The input directories below provide the numerical settings for the Examples
and Benchmarks section. For ABACUS, `INPUT` gives the functional, cutoff,
and SCF tolerance, `STRU` specifies the orbitals and pseudopotentials, and
`KPT` gives the reciprocal-space mesh when it is supplied as a file.

| Case | Input location or archived settings |
| --- | --- |
| Cubic BaTiO₃ | [Unified example](../../3D_Bulk/cubic_BaTiO3/run/). PBEsol, 100 Ry, SCF tolerance 10⁻⁷, Γ-centered 9 × 9 × 9 grid. |
| Tetragonal HfO₂ | [Bulk example](../../3D_Bulk/t_HfO2/run/) and [end-to-end comparison](../../backend_examples/calculator_spectroscopy/). |
| hBN | [BEC example](../../2D_Slab/hBN/run/). The separate open-direction comparison uses a 30 Å cell, 10-bohr B and N orbitals, and a 16 × 16 × 1 SCF mesh. Berry post-processing uses 36 × 36 × 8 and 36 × 36 × 16 grids. |
| α-In₂Se₃ | [PBEsol-D3(0) example](../../2D_Slab/In2Se3_PBEsol/run/). The In and Se orbitals extend to 10 bohr. The input specifies in-plane k-point spacing of 0.1 bohr⁻¹. |
| BN(9,0) | [ABACUS and VASP inputs](../../1D_Nanowire/BN_9_0/run/). Both use a 1 × 1 × 12 mesh. ABACUS uses 10-bohr B and N orbitals. The independent VASP check uses PAW-PBE and a 500 eV cutoff. |
| Sb₂S₃ | [ABACUS inputs](../../1D_Nanowire/Sb2S3/run/) and [VASP finite-displacement inputs and tensors](sb2s3_vasp_fd/). Both use PBE-D3(BJ) and a 1 × 1 × 12 SCF mesh. The open-direction Berry comparison uses 8 × 8 × 20 and 16 × 16 × 20 grids. The ABACUS main case uses 9-bohr orbitals. |
| H₂O and CH₄ molecular BEC | [H₂O](../../0D_Molecules/H2O/), [CH₄](../../0D_Molecules/CH4/). The PBE calculations use 9-bohr orbitals and Γ sampling. The HSE input files are in each case's `results/HSE/` directory. |
| AlN and ZnO | [AlN](../../Piezoelectric_Response/AlN/run/), [ZnO](../../Piezoelectric_Response/ZnO/run/). ABACUS finite strain uses PBE, 8-bohr orbitals, and an 8 × 8 × 6 mesh. |
| MoS₂ spectra in Fig. 10 | [Table 1 geometry comparison](mos2_table1/). The two calculations use the same structure, PBE-D3(BJ), and a Γ-centered 33 × 33 × 1 mesh. ABACUS uses APNS-V1 precision pseudopotentials, 10-bohr numerical orbitals, and 100 Ry. VASP uses Mo_sv and S PAW datasets with 600 eV. |
| CH₄ spectra in Fig. 10 | [ABACUS input](../../IR_Raman_Spectra/Molecule_CH4/run/) and [VASP reference input](ch4_vasp/run/). The VASP spectra use PBE with a 550 eV cutoff at Γ. |

VASP pseudopotentials are supplied by the user. For the MoS₂ ABACUS
input, put the pseudopotentials and numerical orbitals named in `STRU`
in its `assets/` directory.
