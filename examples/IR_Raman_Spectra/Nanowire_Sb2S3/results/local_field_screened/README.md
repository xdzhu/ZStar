# Transverse local-field Raman audit

This is the 26-mode PBE+D3(BJ), original 9 au orbital finite-field correction for the
Sb2S3 isolated chain. The reference geometry, SG15 ONCV pseudopotentials,
orbitals, `INPUT`, and `KPT` remain in the case's `run/` directory. The chain
is periodic along Cartesian z; x and y are vacuum directions.

The original zero-field ABACUS+PYATB Raman calculation overestimates crossed
`yz` intensity. The finite-field calculation reruns ABACUS SCF at x/y fields
of +/-0.0005 a.u. for each +/-0.02 Angstrom sqrt(amu) normal-coordinate
displacement. Transverse response uses real-space dipoles from 12-digit charge
cubes; periodic-z response uses PYATB Berry polarization from the resulting
self-consistent electronic matrices. The symmetric Raman tensor is collected
with `zstar raman screen-1d`. The axial `Rzz` element is retained from the
zero-field PYATB route and **is not a self-consistently screened axial result**.

At 298 K, 532 nm and Lorentzian FWHM 8 cm-1, using one zz normalization per
route and no peak shifts or per-channel fitting:

| Route | max(yz) / max(zz) |
| --- | ---: |
| ZStar (ABACUS), zero-field | 0.39737 |
| ZStar (ABACUS), transverse finite field | 0.00642 |
| ZStar (VASP), screened DFPT | 0.00756 |
| CRYSTAL/B3LYP-D3(BJ) reference | 0.01836 |

The full 26-mode x/y tensor has a maximum unsymmetrized xy reciprocity
residual of 9.58e-5 Angstrom/sqrt(amu). `comparison.json` records all six
polarization-channel ratios. The two PDFs show the original and corrected yz
curves and all six corrected channels; the CRYSTAL reference uses the original
sampled directional spectrum with axes rotated into ZStar's coordinates.
These comparisons establish the weak transverse-channel physics, not
cross-software equality of absolute Raman cross sections.

## Reproduce the spectrum without DFT

From the repository root, run:

```bash
zstar raman spectrum \
  --qpoints examples/IR_Raman_Spectra/Nanowire_Sb2S3/results/qpoints.yaml \
  --tensors examples/IR_Raman_Spectra/Nanowire_Sb2S3/results/local_field_screened/raman_tensors.json \
  --dim 1 --temperature 298 --laser-nm 532 --broadening 8 \
  --incident-polarization 0 0 1 --scattered-polarization 0 1 0 \
  --outdir sb2s3_screened_yz
```

This renders the crossed channel. Change the incident/scattered vectors to
`0 0 1` / `0 0 1` for the axial channel. The tensor file retains the original
mode IDs, so use the archived `qpoints.yaml` and do not renumber the modes.

## Recompute the finite-field tensors

First generate x and y probes from the archived clean inputs:

```bash
python tools/research/sb2s3_abacus_field_probe.py \
  --case examples/IR_Raman_Spectra/Nanowire_Sb2S3 \
  --axis x --all-optical --output sb2s3_field_x
python tools/research/sb2s3_abacus_field_probe.py \
  --case examples/IR_Raman_Spectra/Nanowire_Sb2S3 \
  --axis y --all-optical --output sb2s3_field_y
```

The generated manifests enumerate 106 stages per field axis. Each stage must
complete ABACUS SCF, save `out_chg 1 12` charge cubes and electronic matrices,
then complete periodic-z PYATB polarization. Run these stages through your own
scheduler after configuring ABACUS and PYATB; the original hf-specific launch
scripts are not portable. For each completed SCF stage, the PYATB preparation
and precision-adapted run follow this pattern:

```bash
cd sb2s3_field_x/states/reference/field_plus
abacus
pyatb_input --polar --mp 0.08 --dim 001 --output pyatb-field-polar
cd pyatb-field-polar
python -m zstar.pyatb_precision
```

Apply the same sequence to every stage in both manifests. Do not reuse an
incomplete stage or a default three-digit cube. After both probes finish:

```bash
zstar raman screen-1d \
  --x-probe sb2s3_field_x --y-probe sb2s3_field_y \
  --stru examples/IR_Raman_Spectra/Nanowire_Sb2S3/run/STRU \
  --bare-csv examples/IR_Raman_Spectra/Nanowire_Sb2S3/results/Raman/raman_modes.csv \
  --outdir sb2s3_screened_tensors
```

The complete high-precision raw cubes and electronic matrices remain in the
original calculation archive; they are not duplicated in Git. The archived x/y manifests, per-mode tensor
CSV/JSON/NPY, comparison data and vector figures preserve the compact audit.
The public CRYSTAL dataset is DOI
[10.17632/6tntvw37tr.1](https://doi.org/10.17632/6tntvw37tr.1).
