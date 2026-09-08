# BEC and phonon efficiency benchmarks

Material cases live under physical dimensionality, not a workflow name.
This directory retains timing ledgers, independent force-only controls,
and common offline verification tools.

| Material | Reproducible case |
|---|---|
| Cubic BaTiO3, PBEsol | [cubic_BaTiO3](../3D_Bulk/cubic_BaTiO3/README.md) |
| 3C-SiC, PBE | [SiC](../3D_Bulk/SiC/README.md) |
| Tetragonal HfO2, PBEsol | [t_HfO2](../3D_Bulk/t_HfO2/README.md) |
| alpha-In2Se3, PBE | [alpha_In2Se3_PBE](../2D_Slab/alpha_In2Se3_PBE/README.md) |
| hBN, PBE | [hBN_unified](../2D_Slab/hBN_unified/README.md) |
| MoS2, PBE+D3(BJ) | [MoS2_unified](../2D_Slab/MoS2_unified/README.md) |
| H2O, PBE | [H2O_unified](../0D_Molecules/H2O_unified/README.md) |
| CH4, PBE | [CH4_unified](../0D_Molecules/CH4_unified/README.md) |
| BN(9,0), PBE | [BN_9_0](../1D_Nanowire/BN_9_0/README.md) |
| Sb2S3, PBE+D3(BJ) | [Sb2S3](../1D_Nanowire/Sb2S3/README.md) |

Run from the repository root:

```bash
bash examples/3D_Bulk/SiC/run.sh
python examples/Benchmarks/run_control.py SiC --prepare-only
python examples/Benchmarks/verify.py
python examples/3D_Bulk/cubic_BaTiO3/verify.py
```

The first command requires configured ABACUS and PYATB. Verification uses
temporary copies of archived outputs and requires neither solver.
Each material has clean `run/` inputs and basis files, archived `results/`,
and a separate `work/` for new execution. Install `zstar==0.3.1` and use
the matching GitHub tag for frozen example inputs.

## Timing definition

Unified obtains BEC and Gamma force constants from the same SCFs. Separate
adds independently executed force-only SCFs to the Cartesian BEC cost.
Cubic BaTiO3 retains its historical forward BEC timing; the other nine
comparisons use central differences. The reference-state comparison
separately lists prepared central-displacement counts for every system.
Prepared counts do not change the measured forward timing denominator.

The [independent phonon archive](independent_phonons/README.md) contains the
measured additional force tasks. Original Cartesian joint-response controls
remain for reconstruction checks. Successful ABACUS/PYATB solver times
include reference and band-gate work, but exclude relaxation, setup, transfer
and unmeasured interrupted attempts. Historical force-output overhead is not
subtracted from the Cartesian BEC timings.

The default step is 0.02 bohr; derivatives use actual written STRU differences.
The unstable cubic BaTiO3 reference does not support a stable static phonon
dielectric constant. Raman adds PYATB dielectric derivatives, not new SCFs,
when matrices are retained; see the [Unified spectroscopy guide](../../docs/unified_spectroscopy.md).
Full phonon dispersions still require additional calculations.

Historical machine-readable names such as `shared_response.json` and original
result-scheme keys remain unchanged for compatibility and evidence integrity.
They are not the public case-directory taxonomy.
