# 2D MoS2: IR and Raman

## Unified Workflow

`bash run.sh` now uses the Unified BEC/force/dielectric response ensemble.
`bash run.sh --method mode --work mode_control` retains the independent mode-FD route.
The additional Raman step reuses electronic matrices and does not add SCFs.

`results/Unified/` contains the four-dimensional efficiency-benchmark results,
including hash-checked displacement observations, IR/Raman tables and plots,
and `efficiency.json`. These are Gamma-ensemble benchmarks; older spectra in
other result folders retain their original geometry/supercell conventions.

```bash
bash run.sh --dry-run
bash run.sh --post-only
```

The second command regenerates the archived Unified spectra without DFT into
`work-unified-post/`, using the public reconstruction and spectrum kernels.
See the [English tutorial](../../../docs/unified_spectroscopy.md) and
[中文教程](../../../docs/unified_spectroscopy.zh-CN.md).

This monolayer MoS2 case uses PBE+D3(BJ). Inputs and the matching ABACUS
assets are under `run/`; the retained `results/` directory contains IR/Raman
mode tables and spectra, including the 2D sheet Raman response.

```bash
bash run.sh --dry-run
ABACUS_COMMAND="mpirun -np 20 abacus" PYATB_COMMAND="pyatb" bash run.sh
```

The out-of-plane BEC convention remains the cube-integrated 2D route. The
spectral response is reported as a sheet response and must not be interpreted
as a vacuum-dependent bulk dielectric tensor.

## Paper result archive

`results/bec/` contains the original seven-stage forward BEC evidence, including
the reference electronic tensor in `BORN`, full-cell `Z-BORN-symm.out`, written
structures, PYATB inputs, Berry outputs, and integrated open-axis observations.
`source_manifest.json` records original file hashes. Mo has in-plane BEC
`-0.80585922 e`; this is not the older `2D_Slab/MoS2` quick-start dataset.
`results/dielectric_response/` holds the paper's phonon-only sheet response.
`results/phonon/` preserves the exact paper post-processing inputs. Its mode
frequencies, eigenvectors, and symmetry labels equal those in `results/bec/`.
The compact structural metadata uses angstrom rather than bohr and masses of
95.95/32.06 amu rather than the solver's 95.96/32.065 amu. This small mass
rounding affects response normalization, not the retained frequencies. The
provenance manifest records both representations; do not mix their metadata.
The omission of the electronic term in that plot is a presentation choice,
not evidence that the reference electronic response was uncomputed.

The retained spectra use a 3x3x1 phonon supercell (11x11x1 force mesh), a
33x33x1 primitive-cell SCF mesh, PBE+D3(BJ), and a 1e-8 SCF threshold.
The current `run.sh` creates the Unified Gamma workflow; it does not claim to
repeat the archived supercell displacement ensemble byte for byte.
To regenerate the archived dielectric curve without DFT:

```bash
zstar dielectric freq --qpoints results/phonon/qpoints.yaml \
  --born results/bec/Z-BORN-symm.out --dim 2 --broadening 8 \
  --outdir work-dielectric
```

Results remain read-only inputs; newly generated files go to `work-*`.
