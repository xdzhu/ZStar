# Molecule CH4: IR and Raman

## Unified Workflow

`bash run.sh` now uses the Unified BEC/force/dielectric response ensemble.
The additional Raman step reuses electronic matrices and does not add SCFs.
The molecular APT path is experimental; see the [validation and limitations](../../Benchmarks/Molecular_APT_Safety/README.md).

`results/Unified/` contains the four-dimensional efficiency-benchmark results,
including hash-checked displacement observations, IR/Raman tables and plots,
and `efficiency.json`. These are Gamma-ensemble benchmarks; older spectra in
other result folders retain their original geometry/supercell conventions.

The archived IR results used the previous molecular response and do not have
a matching APT validation receipt. They are retained for historical context,
not as validated current IR results; `--post-only` is disabled for this archive.
Retained Raman curves likewise have their own response and intensity limits.
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
