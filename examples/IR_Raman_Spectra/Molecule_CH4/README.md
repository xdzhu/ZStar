# Molecule CH4: IR and Raman

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

This isolated methane case uses `dim=0` with a large periodic box. It provides
an ABACUS + PYATB molecular IR/Raman quickstart; the response is molecular and
is not a bulk dielectric function.

```bash
bash run.sh --dry-run
ABACUS_COMMAND="mpirun -np 20 abacus" PYATB_COMMAND="pyatb" bash run.sh
```

The clean PBE inputs and pseudopotentials/orbitals are under `run/`. The structure
is the relaxed Unified benchmark reference, with `scf_thr=1e-8` and
`gamma_only=0` for PYATB matrix export. Earlier quickstart inputs are preserved
under `legacy/before_acceptance_20260906/`; they are not the benchmark geometry.
This runner starts from the supplied relaxed structure; it does not relax it again.
Retained
mode tables and spectra are under `results/`; generated phonon and response
stages go to `work/`.
