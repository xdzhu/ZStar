# Bulk HfO2: IR and Raman

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

This tetragonal HfO2 case uses PBEsol, 9-bohr numerical orbitals,
100 Ry, a 10x10x7 Gamma-centered mesh and SCF threshold 1e-8.
The input and matching
assets are under `run/`; compact IR/Raman tables, spectra, and plots are under
`results/`.

Run `bash run.sh --dry-run` first. A real run performs the serial BEC/phonon
workflow, contracts the BEC with phonon modes for IR, and calculates
additional polarizability derivatives for Raman:

```bash
ABACUS_COMMAND="mpirun -np 20 abacus" PYATB_COMMAND="pyatb" bash run.sh
```

The retained Raman record contains all 15 optical modes. The compact reference
uses a 532 nm laser and 8 cm-1 broadening. Scratch data are written to `work/`.

`results/provenance.json` identifies the validated data. Older input
settings are retained only in `legacy/before_20260906/`. The default unified
BEC/force ensemble has four displacements plus its reference. The 15 optical
Raman mode-difference control requires 30 further positive/negative response
stages. The default Unified route instead evaluates static dielectric responses
on the existing five electronic structures, with no additional SCFs.
