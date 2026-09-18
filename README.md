<p align="center">
  <img src="docs/logo.png" alt="ZStar logo" width="128">
</p>

<h1 align="center">ZStar</h1>

<p align="center">
  A unified toolkit for polarization, Born effective charges, dielectric and piezoelectric responses, and infrared and Raman spectra
</p>

<p align="center">
  <a href="https://pypi.org/project/zstar/"><img alt="PyPI" src="https://img.shields.io/pypi/v/zstar"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-GPL--3.0-green"></a>
</p>

<p align="center">
  English | <a href="README.zh-CN.md">简体中文</a> |
  <a href="docs/user_guide.md">Full manual</a> |
  <a href="docs/README.en.pdf">PDF</a>
</p>

## Quick Start

The two-atom **3C-SiC** example calculates BEC and Gamma-point phonons from
the same symmetry-adapted calculations, then produces IR and Raman spectra.
Its ABACUS inputs, SG15 pseudopotentials, DZP orbitals, and reference results
are included.

### 1. Install

Without the examples, just run `pip install zstar`. To reproduce SiC:

```bash
git clone https://github.com/xdzhu/ZStar.git
cd ZStar
pip install .
```

### 2. Configure the calculators

Install [ABACUS](https://github.com/deepmodeling/abacus-develop)
([LTSv3.10.0 recommended](https://github.com/deepmodeling/abacus-develop/releases/tag/LTSv3.10.0))
and [PYATB](https://github.com/pyatb/pyatb). Phonopy is installed with ZStar.
Follow the [configuration guide](docs/cli_reference.md#calculator-configuration)
to set executable paths and MPI/OMP, then check:

```bash
zstar config check
```

Continue once ABACUS and PYATB both report `available`.

### 3. Calculate BEC and Gamma phonons

Make a working copy, keeping the supplied inputs and archived results intact:

```bash
cd examples/3D_Bulk/SiC
cp -r run work
cd work

zstar bec pre --stru STRU
zstar bec run
zstar bec post
```

Outputs include `BEC.dat`, `BORN`, `FORCE_CONSTANTS`, and `qpoints.yaml`.
Expect opposite Si/C diagonal BEC values near **2.70 e** and an optical triplet
near **773 cm^-1**. Use `zstar bec stat` to check progress; rerunning skips
completed stages.

### 4. Generate IR and Raman spectra

```bash
zstar spectra pre --root spectra --response .
zstar spectra run --root spectra
zstar spectra post --root spectra
```

Plots and tables are written to `spectra/ir/` and `spectra/raman/`.
[Archived SiC spectra](examples/3D_Bulk/SiC/results/spectra) are available
without running DFT. See the [case tutorial](examples/3D_Bulk/SiC/README.md)
for dry runs, progress checks, and the optional `run.sh` launcher.

## agent skill

Run `zstar skill install`, then start a new agent session and invoke
`$run-zstar-workflows`. An [example prompt](docs/user_guide.md#5-let-an-agent-run-the-same-workflow)
covers installing ZStar and its skill, configuring the calculators, and
reproducing SiC from scratch.

## Examples and Documentation

![IR and Raman spectra for bulk crystals, slabs, nanowires, and molecules](docs/paper_figures/spectroscopy_across_dimensions.png)

- [Full manual](docs/user_guide.md) ([PDF](docs/README.en.pdf)): detailed workflows, BEC/APT results, efficiency benchmarks, and validation figures.
- [Documentation index](docs/README.md): configuration, dimensional conventions, schedulers, and task-specific guides.
- [Example library](examples/README.md): bulk, slab, wire, and molecular cases, each with `run/`, `results/`, and `run.sh`.
- [VASP native response](docs/vasp_native_response.md): bulk BEC, dielectric, phonon, piezoelectric, and elastic workflows; [other calculators](docs/calculator_independent_backends.md).

## Citation and License

Please cite ZStar and the underlying calculators used in your work; see
[CITATION.cff](CITATION.cff). Licensed under [GPL-3.0](LICENSE).
