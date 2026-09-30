# Cs2SnO3 Gamma-mode stability audit

This post-processing benchmark distinguishes acoustic drift from a genuinely
non-translational imaginary Gamma mode. It uses eigensystems from the
Cs2SnO3/PBEsol calculations made for the RamanDB material `mp-867730`
comparison. No VASP executable or licensed `POTCAR` is distributed here.

## Run

Install ZStar and Phonopy from the repository root, then run:

```bash
cd examples/Benchmarks/cs2sno3_gamma_modes/run
bash run.sh
zstar phonon inspect --qpoints conventional/qpoints.yaml
zstar phonon inspect --qpoints raw_primitive/qpoints.yaml
```

`run.sh` checks three eigensystems and writes `run/output/mode_audit.json`.
The checked result is retained in `results/expected_mode_audit.json`.
The `inspect` command can also write machine-readable output with `--json`.

## Result

| Eigensystem | Imaginary Gamma modes | Classification |
| --- | --- | --- |
| 24-atom conventional-cell VASP/PBEsol | -3.030, -1.471, -1.096 cm^-1 | All are translations; overlaps 0.9948-0.9999. |
| 12-atom primitive VASP/PBEsol DFPT, raw | -23.167, -5.364, -1.273 cm^-1 | The first is mixed (translation overlap 0.6681); the other two are translations. |
| Same primitive force constants after Phonopy symmetrization/acoustic sum rule | -21.536 cm^-1 | Non-translational optical mode; translation overlap below 0.0001. |

The default 20 cm^-1 tolerance now applies **only to a mode identified as a
rigid translation**. A small imaginary internal mode is not silently accepted.
The mixed raw primitive mode requires further inspection; after the acoustic
sum rule, its optical component remains imaginary. The conventional-cell
result demonstrates why a small negative frequency alone is not evidence of
an optical instability.

This audit classifies modes; it does not prove why primitive-cell VASP DFPT
and the independent finite-displacement calculation disagree about the
restoring force. The earlier independent finite-displacement control gave a
positive primitive-cell optical mode, and the database-setting supercell
calculation gave approximately +1.224 THz. Do not label the raw primitive
DFPT result a verified physical instability. The separate shallow off-Gamma
acoustic feature is not a Gamma-point mode and is outside this check's scope.

## Provenance

The two `qpoints.yaml` files are derived from the authors' VASP/PBEsol
calculations, not copied from RamanDB. The primitive-cell force constants are
from the 4x4x3-k-mesh DFPT control; `reproduce.py` applies Phonopy's
`symmetrize_force_constants()` before recomputing Gamma eigenvectors. Both
NAC and frequency shifts are disabled. The four archived numeric inputs are:

```text
0be03b74c58510564bdccc50d84fcf9c274fa486c34ea3f29a3d4926605c1bd8  run/raw_primitive/qpoints.yaml
ba2aae3dd30688acf7672c62630748664f0f224f1ac989bc58ccfeb44e462cf1  run/conventional/qpoints.yaml
f0747183b41401ed0fb2bc0f86b281144f35261751cbc6196074dee99723e052  run/asr_primitive/FORCE_CONSTANTS
ad9b833cb256059c7b2a036e86dd5d383d060f84f62f8024a1715faa1a93240d  run/asr_primitive/phonopy.yaml
```

Phonopy's [output-file reference](https://phonopy.github.io/phonopy/output-files.html)
defines its mass-weighted dynamical-matrix eigenvectors. Its
[force-constant documentation](https://phonopy.github.io/phonopy/setting-tags.html#fc-symmetry)
describes the translational acoustic sum rule used in the control above.
