<p align="center">
  <img src="docs/logo.png" alt="ZStar logo" width="160">
</p>

<h1 align="center">ZStar</h1>

<p align="center">
  A unified toolkit for polarization, Born effective charges, dielectric and piezoelectric responses, and infrared and Raman spectra
</p>

<p align="center">
  <a href="https://pypi.org/project/zstar/"><img alt="PyPI" src="https://img.shields.io/pypi/v/zstar"></a>
  <a href="https://pypi.org/project/zstar/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/zstar"></a>
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

Requires Python 3.9 or newer; the core symmetry routines use spglib without
requiring pymatgen. The examples are on GitHub, not in the PyPI wheel.

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
zstar bec run --dry-run
zstar bec run
zstar bec stat
zstar bec post
```

`pre` prepares the reference and symmetry-adapted displacements; `run` checks
the reference band gap and executes the calculations; `post` jointly
reconstructs BEC and Gamma force constants. Outputs include `BEC.dat`, `BORN`,
`FORCE_CONSTANTS`, and `qpoints.yaml`. Expect opposite Si/C diagonal BEC values
near **2.70 e** and an optical triplet near **773 cm^-1**. Rerunning resumes
incomplete stages.

### 4. Generate IR and Raman spectra

```bash
zstar spectra pre --root spectra --response .
zstar spectra run --root spectra
zstar spectra stat --root spectra
zstar spectra post --root spectra
```

IR uses the completed BEC and phonon data. Raman adds PYATB dielectric-response
calculations using the existing electronic matrices, without additional SCFs
in the Unified route. Plots and tables are written to `spectra/ir/` and
`spectra/raman/`.
[Archived SiC spectra](examples/3D_Bulk/SiC/results/spectra) are available
without running DFT. See the [case tutorial](examples/3D_Bulk/SiC/README.md)
for dry runs, progress checks, and the optional `run.sh` launcher.

## Unified Response Framework

The ABACUS + PYATB workflow uses Phonopy's symmetry-adapted displacements to
jointly reconstruct BEC/APT tensors and zone-center force constants from the
same polarization and force calculations. Reusing their electronic matrices
also supplies the derivatives required for nonresonant Raman spectra.

![ZStar Unified workflow](docs/paper_figures/unified_workflow.png)

The reference-first, serial workflow checks the band gap and reuses copies of
the converged `0.no-move` charge density. Restartable reconstruction uses actual
displacement vectors and symmetry, retaining raw and sum-rule-corrected tensors
with residual diagnostics.

| Capability | Main results |
| --- | --- |
| Polarization and BEC/APT | Branch-matched polarization, full tensors, `BORN`, response records |
| Gamma phonons | Force constants, mode frequencies, eigenvectors, irreducible representations |
| IR and Raman | Mode charges, oscillator strengths, Raman tensors, polarized/broadened spectra |
| Dielectric response | Electronic, phonon, static, and frequency-dependent response |
| Supercell phonons | High-symmetry phonon bands, DOS, bulk NAC and LO-TO splitting |
| Piezoelectric response | Native VASP clamped/ionic/total `e`; elastic response and derived `d` |
| Polarization-related potential analysis | Planar maps, line profiles, vacuum potential steps, mirror asymmetry |

Details: [Unified BEC/phonons](docs/research/shared_response/USAGE.md),
[Unified spectroscopy](docs/unified_spectroscopy.md), and
[numerical validation](docs/validation.md).

## Systems of Different Dimensionalities

Periodic directions use phase-wrapped Berry-phase polarization; open directions
use electronic plus ionic real-space dipoles. Molecules use atomic polar tensors (APT).

| `--dim` | System | Response treatment and examples |
| --- | --- | --- |
| `3` | Bulk crystal | Berry-phase polarization; cubic BaTiO3, tetragonal HfO2, SiC |
| `2` | Slab | In-plane Berry phase and out-of-plane cube dipole; hBN, MoS2, alpha-In2Se3 |
| `1` | Wire or tube | Axial Berry phase and transverse cube dipoles; BN(9,0), Sb2S3 |
| `0` | Molecule | Dipole derivatives and APT; H2O, CH4 |

For a slab, use `zstar bec pre --stru STRU --dim 2`; later stages retain this
choice. Hybrid slabs/wires must align their normal/axis with Cartesian `z`
and require converged vacuum size.

For a periodic crystal, the tensor convention is polarization first:

$$
Z^*_{\kappa,\alpha\beta}=\frac{\Omega}{e}\frac{\partial P_\alpha}{\partial u_{\kappa\beta}}.
$$

Low-dimensional outputs use molecular, line, or sheet polarizability, not
vacuum-dependent bulk permittivity. See [response conventions](docs/response_conventions.md)
for units, thickness conversion, and perpendicular-field boundary conditions.

## Representative BEC and APT Results

The examples retain full tensors, settings, and provenance for these selected values:

| System | XC | Representative result, in `e` |
| --- | --- | --- |
| [Cubic BaTiO3](examples/3D_Bulk/cubic_BaTiO3) | PBEsol | `Z*(Ti) = 7.440`; `Z*(Ba) = 2.734` |
| [Tetragonal HfO2](examples/3D_Bulk/t_HfO2) | PBEsol | `Z*(Hf,xx) = 5.394`; `Z*(Hf,zz) = 4.828` |
| [Monolayer hBN](examples/2D_Slab/hBN_unified) | PBE | `Z*(B,parallel) = 2.702`; `Z*(B,z) = 0.343` |
| [Alpha-In2Se3](examples/2D_Slab/alpha_In2Se3_PBE) | PBE | `Z*(In(2),parallel) = 4.016`; `Z*(In(2),zz) = 0.278` |
| [BN(9,0)](examples/1D_Nanowire/BN_9_0) | PBE | `(Zrr,Ztt,Zzz)_B = (0.397,1.256,2.745)` |
| [H2O](examples/0D_Molecules/H2O_unified) | PBE | `q_GAPT(O) = -0.481`; `q_GAPT(H) = +0.240` |
| [CH4](examples/0D_Molecules/CH4_unified) | PBE | `q_GAPT(C) = -0.021`; `q_GAPT(H) = +0.005` |

These are ABACUS + PYATB results; molecular `q_GAPT = Tr(APT)/3` is not a
periodic-crystal BEC. H2O/CH4 also include HSE cube-dipole APT summaries;
see the [molecular guide](docs/molecular_spectroscopy.md).

## IR, Raman, and Dielectric Response

![IR and Raman spectra for bulk crystals, slabs, nanowires, and molecules](docs/paper_figures/spectroscopy_across_dimensions.png)

Rows show tetragonal HfO2 (PBEsol), MoS2 (PBE-D3(BJ)), Sb2S3, and CH4.
[Spectroscopy examples](examples/IR_Raman_Spectra) retain mode assignments and
reference data, including the Sb2S3 computational-dataset reference and its
observed Raman-intensity differences.

Continue from the Quick Start's completed BEC/Gamma outputs to calculate static
and frequency-dependent dielectric response:

```bash
zstar dielectric static --qpoints qpoints.yaml --born BEC.dat --dielectric BORN --dim 3
zstar dielectric freq --qpoints qpoints.yaml --born BEC.dat --dielectric BORN --dim 3
```

![Bulk and slab dielectric-response examples](docs/paper_figures/dielectric_response_examples.png)

HfO2 shows electronic plus phonon response; MoS2 shows phonon sheet polarizability.
Outputs include static tensors, real/imaginary data, and PNG/PDF/SVG plots.
The [dielectric guide](docs/dielectric_response.md) explains damping,
mode cutoffs, normalization, and optical constants.

Finite-q bands/DOS require a **separate supercell calculation**, not just Gamma
force constants. The [phonon tutorial](docs/phonon_spectrum.md) covers automatic
supercells, custom CPU/GPU `INPUT`, paths, and bulk NAC: two without/with-NAC
plots plus a LO-TO-splitting overlay, using a compatible `BORN` file.
Bulk NAC is not applied to slabs or wires.

## Calculators and Piezoelectric Response

Other calculators use their documented solvers, not necessarily the Unified route.
Install `zstar[vasp]` when optional VASP readers are needed.

| Calculator | Supported route | Guide |
| --- | --- | --- |
| ABACUS + PYATB | Unified BEC/APT, Gamma phonons, IR/Raman, dielectric response | [Unified workflow](docs/research/shared_response/USAGE.md) |
| VASP | Native bulk BEC/dielectric/phonon response, IR, piezoelectric/elastic tensors; mode-displaced Raman | [Native response](docs/vasp_native_response.md) |
| CP2K | Dipole-based BEC/APT and native spectroscopy routes | [BEC](docs/cp2k_bec.md), [spectra](docs/calculator_spectroscopy.md) |
| Quantum ESPRESSO | Native DFPT BEC, dielectric, and IR collection | [Backend guide](docs/calculator_independent_backends.md) |

For example, obtain relaxed-ion piezoelectric `e` from prepared VASP inputs:

```bash
zstar bec pre --calculator vasp --input-dir input --root piezo --piezo
zstar bec run --root piezo
zstar bec post --root piezo
```

VASP uses native DFPT/ionic response for LDA/GGA; `--elastic` additionally
provides the elastic matrix and derived `d`. [SiC](examples/VASP_Native_Response/3C_SiC)
and [AlN](examples/VASP_Native_Response/AlN) retain validation results. Raman
needs additional mode-displaced calculations. Supply licensed `POTCAR` locally;
see the guides for functional and low-dimensional boundaries.

## Running Your Own Structures and Cluster Jobs

Place your ABACUS inputs and assets in a working directory. If pseudopotentials
or orbitals are elsewhere, supply their directories during preparation:

```bash
zstar bec pre --stru STRU --pp /path/to/PSEUDO --orb /path/to/ORBITAL
zstar bec job --system slurm
```

Ambiguous asset matches stop with guidance; the original `STRU` is preserved.
Configure executables and MPI/OMP with `zstar config`; put queues, allocations,
modules, and environment commands in the header. Selection is **Specified**
(`--header`) > **Current** (`./header.sh`) > **Global** (`~/.zstar/header.sh`),
without merging; otherwise an editable template is generated.

`job` generates a driver, not a running calculation: inspect, submit, wait, then
`post`. Shell, Slurm, and Torque/PBS are supported. [Headers](docs/job_headers.md)
and [CLI options](docs/cli_reference.md) cover resources and global PP/ORB settings.
New PYATB builds use direct static response; older builds use a compact optical
grid. See [compatibility](docs/user_guide.md#pyatb-compatibility).

## Measured Efficiency

Matched Separate/Unified benchmarks reach **3.98x** speedup for BEC/APT plus
Gamma phonons and **8.35x** for combined IR/Raman. Bars show normalized cost,
absolute solver CPU core-hours, and speedup.

![Measured Separate and Unified workflow costs](docs/paper_figures/unified_efficiency_benchmarks.png)

The [benchmark archive](examples/Benchmarks/README.md) retains task counts,
timing boundaries, and data; speedups depend on the case and settings.

## Polarization-Related Potential Analysis

`zstar pot` produces tiled maps, line profiles, vacuum steps, and mirror-asymmetry
diagnostics for MoS2, alpha-In2Se3, and SnS/SnSe/SnTe potential cubes.

![Polar slab and in-plane potential examples](docs/paper_figures/potential_examples_2d.png)

Alpha-In2Se3 gives a vacuum step near **1.221 eV**; MoS2 is nearly symmetric.
See the [potential tutorial](docs/potential_examples.md) and
[runnable cases](examples/Electrostatic_Potential).

## agent skill

Install the packaged `$run-zstar-workflows` skill, then open a new agent session:

```bash
zstar skill install
```

Example request: "Use $run-zstar-workflows to copy the supplied SiC inputs into
a new workspace, check the calculator configuration, and run the BEC, Gamma
phonon, and IR/Raman stages. Report the tensors, frequencies, and output paths."

If ZStar is not installed yet, the [from-scratch prompt](docs/user_guide.md#5-let-an-agent-run-the-same-workflow)
specifies source, Python-environment, skill, and workspace locations. The
[skill guide](docs/agent_skill.md) covers refresh and preflight checks.

## Documentation and Command Map

[Full English manual](docs/user_guide.md) ([PDF](docs/README.en.pdf)) |
[完整中文手册](docs/user_guide.zh-CN.md) ([PDF](docs/README.zh-CN.pdf)) |
[Task-based documentation](docs/README.md) | [Example library](examples/README.md)

Examples separate clean inputs in `run/`, retained results in `results/`, and a
resumable `run.sh`; learn the individual stages above before using the launcher.

| Command family | Purpose |
| --- | --- |
| `zstar bec pre/job/run/stat/post` | Polarization, BEC/APT, Unified Gamma outputs or native backend response |
| `zstar phonon pre/job/run/stat/post/irrep/spectrum` | Supercell forces, modes, activity classification, bands and DOS |
| `zstar spectra pre/job/run/stat/post` | IR and Raman preparation, execution, collection, and plotting |
| `zstar dielectric static/freq/optics` | Static/frequency response and optical constants |
| `zstar config init/show/set/check` / `zstar backend list` | Configuration and calculator availability |
| `zstar response` / `zstar density` | Response interchange and density-export adapters |
| `zstar stru convert/wyckoff` | Structure conversion and Wyckoff inspection |
| `zstar data db/qnep` | Traceable BEC database and qNEP export |
| `zstar skill install/path/preflight` / `zstar pot` | agent skill and potential analysis |

The [CLI reference](docs/cli_reference.md) lists all actions and aliases;
full guides contain detailed settings and conventions.

## Citation and License

Please cite ZStar and the underlying electronic-structure and lattice-dynamics
programs used in your work; see [CITATION.cff](CITATION.cff).
ZStar is distributed under [GPL-3.0](LICENSE). Copyright (c) Xudong Zhu.
