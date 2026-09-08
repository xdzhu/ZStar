# ZStar Reproducible Examples

This directory is the public, curated example library for ZStar. Each material
case keeps the smallest useful set of inputs, calculator assets, provenance,
and compact reference results. Full ABACUS, PYATB, CP2K, or VASP scratch
directories are intentionally excluded.

## Layout

| Directory | Scope | Cases |
|---|---|---|
| `3D_Bulk/` | bulk BEC and dielectric response | tetragonal and cubic BaTiO3, HfO2, 3C-SiC |
| `2D_Slab/` | slab and vacuum-independent sheet response | MoS2, hBN, alpha-In2Se3 |
| `1D_Nanowire/` | periodic one-dimensional response | BN(9,0), Sb2S3; earlier GaAs example |
| `0D_Molecules/` | molecular APT, IR, and Raman | H2O, CH4, CO2 |
| `backend_examples/` | calculator-specific validation | CP2K BEC/IR/Raman; ABACUS/VASP SiC and HfO2 benchmarks |
| `IR_Raman_Spectra/` | one-command IR and Raman workflows | HfO2, MoS2, Sb2S3, CH4, BN nanotubes; earlier GaAs example |
| `Electrostatic_Potential/` | cube-based electrostatic-potential analysis | MoS2, alpha-In2Se3, GeS, SnS, SnSe, SnTe |
| `Benchmarks/` | matched Unified/Separate BEC/APT and Gamma-Hessian efficiency | cubic BaTiO3, SiC, t-HfO2, alpha-In2Se3, hBN, MoS2, H2O, CH4, BN(9,0), Sb2S3 |

The machine-readable index is `manifest.json`; `path_migration.json` maps older
paths to the dimension-based layout. `Benchmarks/` indexes paired comparisons,
while the material inputs now live in the four dimensionality directories.
Historical result records retain their original paths as provenance.
Every indexed case contains a clean
`run/` input directory, a `results/` directory with retained outputs, a
bilingual README, and a root-level `run.sh`. The reference files are
provenance-bearing validation records, not a substitute for convergence
testing on a new machine. A complete directory layout does not imply that every
case includes the upstream DFT data: see the reproduction levels below.

## Reproduction levels

- **Electronic-structure rerun:** run the supplied inputs with configured external
  calculators and the case's assets. Licensed VASP inputs remain user-supplied.
- **Offline reconstruction:** regenerate numerical outputs from retained response
  observations or a retained cube, without running DFT. The four Unified spectra
  examples provide `bash run.sh --post-only`; their inputs are hash checked.
- **Supplied-result analysis:** inspect retained tables and figures, or supply the
  original kind of solver output to rerun postprocessing. SnS, SnSe and SnTe
  potential cases require `bash run.sh --cube /path/to/ElecStaticPot.cube`.

Potential scripts for MoS2, In2Se3 and GeS also expect an existing cube; they do
not launch the upstream SCF automatically. `GeS_nonpolar` has its own runner and
retained compressed cube. Follow each case README before starting a calculation.

## Quick start

The two-atom 3C-SiC case is the shortest complete BEC and spectroscopy example.
After configuring ABACUS and PYATB, run:

```bash
cd examples/3D_Bulk/SiC
bash run.sh --with-spectra --dry-run
bash run.sh --with-spectra
```

The script seeds a sibling `work/` directory, preserves existing stages, and
resumes after interruption. It writes the Unified BEC/Gamma response under
`work/` and the IR/Raman plots under `work/spectra/`. Use the case README for
the exact inputs and outputs. Other cases follow the same `run/`, `results/`,
and `work/` convention, with dimensionality-specific details stated locally.

## Reproducibility contract

- Run commands from the case work directory so relative asset paths remain
  visible.
- Keep `run/` and `results/` unchanged; write new outputs to `work/`.
- `dim=0`, `1`, `2`, and `3` mean molecule, periodic wire, slab, and bulk.
- For `dim=2`, in-plane polarization uses the Berry-phase route while the
  out-of-plane component uses the charge-density cube integration route.
- For `dim=1`, transverse dipoles use real-space integration and a bulk NAC
  correction must not be enabled.
- Bulk ranking and dielectric constants require a converged insulating state;
  molecular, wire, and slab responses must be reported with their intrinsic
  dimensional normalization.

## Validation only

The backend examples document how to connect ZStar to CP2K and VASP. Licensed
files such as VASP `POTCAR` are not redistributed. See
`docs/calculator_independent_backends.md`, `docs/calculator_spectroscopy.md`,
`docs/spectroscopy_backend_benchmark.md`,
and the individual case READMEs for calculator-specific setup.

The `Electrostatic_Potential/SnS`, `SnSe`, and `SnTe` cases are compact
post-processing examples: they retain verified profiles and plots, while the
upstream raw cube and large SCF outputs remain outside the public package.
