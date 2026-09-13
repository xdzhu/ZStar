# Compatibility with charge-aware machine-learning force fields

ZStar can prepare calculator-neutral reference data for charge-aware machine-
learning force fields. Its role is to generate and audit first-principles
response labels, not to train a force field. A dataset may contain energy,
force, and stress/virial labels for every frame while BEC labels are computed
only for a representative subset. Missing BECs remain explicit (`null` plus
`born_effective_charges_available: false`) and are never replaced with a zero
matrix.

The `zstar data` actions provide a small, reusable bridge:

```text
zstar data inspect  --input dataset.jsonl
zstar data select   --input dataset.jsonl --output selected.jsonl --count 64 --seed 7 --temperature-bin 300 --temperature-bin 500
zstar data annotate --input selected.jsonl --map frame_bec.csv --output labeled.jsonl
zstar data validate  --input labeled.jsonl --report validation.json
zstar data export    --input labeled.jsonl --output train.xyz
```

DeepMD datasets can be used as the force-field side of the same workflow
without installing `dpdata`:

```text
zstar data inspect --input deepmd_npy/ --metadata frame_metadata.csv
zstar data select --input deepmd_npy/ --metadata frame_metadata.csv \
  --output selected.jsonl --count 100 --seed 17 \
  --temperature-bin 300 --temperature-bin 500
```

The reader accepts the standard `deepmd/npy` layout (`set.*`, `coord.npy`,
`box.npy`, `energy.npy`, `force.npy`, optional `virial.npy`, `type.raw`, and
`type_map.raw`). A metadata CSV is deliberately explicit: ZStar does not infer
temperature or phase from directory names. The selected JSONL frames can then
be passed through the existing BEC preparation workflow, and the resulting BEC
files can be attached with `zstar data annotate`. The same sidecar may carry
`total_charge` and `split` columns so charge state and train/validation/test
membership remain explicit.

For a sparse-label campaign that only needs Born tensors, the unified collector
also accepts `zstar deal --pyatb --bec-only`. This writes `BEC.dat`,
`BEC.rep.dat`, and response-fit diagnostics without requiring a PYATB
optical/static-dielectric output. Static dielectric data remain mandatory for
NAC/BORN phonon output.

Generic ASE extended-XYZ datasets are accepted through the same reader, including
common MACE exports with `REF_energy`, `REF_forces`, and `REF_stress` fields.
DeepMD, MACE, and other force-field formats are only source adapters: after
representative structures are selected, the same DFT/BEC workflow is used for
all of them.

An ABACUS calculation directory containing `STRU` and `OUT.*` can also be
normalized through the optional `dpdata` adapter. It reads labelled
coordinates, energies, forces, and virials when the installed dpdata version
supports the corresponding ABACUS format; BECs are still attached separately
from the ZStar/PYATB response workflow. `dpdata` is not a dependency of the
ordinary ZStar installation.

The finite-displacement SCFs already paid for by a BEC workflow (the `N_SCF`
SCF steps in that response family) can also be reused as a
small force-only support set. `examples/.../run/collect_bec_batch.py
--force-only-output` extracts the completed `0.no-move` and `disp-*` SCF
energies and forces, while keeping BEC explicitly unavailable on those rows.
Each row records its `parent_frame_id`, displacement identifier/vector, and SCF
provenance. A family is rejected if any member is incomplete, and splits must
be made by parent frame because these displacements are correlated. The completed
Wuzhen campaign yielded 612 such rows from 65 complete parents; the neutral
manifest is checked in while the raw JSONL remains scratch-only. Two
incomplete parents are withheld rather than padded with zeros. This is an auxiliary label family, not an
independent validation set or a replacement for
a consistently generated r2SCAN energy/force/virial pool.

The force-only JSONL follows the same export path,
`zstar data export --input force_only.jsonl --output force_only.xyz`, and can
be audited with `zstar qnep check`; a zero BEC-label count is expected for this
auxiliary file.

For a compatibility demonstration, keep the force-field pool at roughly
200--500 frames and compute BECs for representative frames. The current
cubic-BaTiO3 example uses 169 unique completed ABACUS/PBEsol DFT frames
(119 primitive and 50 2x2x2), with two primitive BEC labels and 167 explicit
missing-BEC states. Existing DFT outputs are collected verbatim; no energy
shift, normalization, or rerun is performed. Duplicate geometries are reported
and removed deterministically after raw-label agreement is checked. The older
`qnep_export/train_qnep_249_sparse62.xyz` file remains only as a public-source
parser fixture and must not be used for final accuracy or phonon claims. This
is sufficient to demonstrate data preparation, sparse response labels, and a
downstream harmonic phonon/NAC check; it is not intended to establish
production-level qNEP accuracy.

The schema records stable frame IDs, structure IDs, atom order, cell/positions,
total charge, optional polarization/dipole/BEC, temperature, phase, units,
coordinate convention, calculator and DFT provenance. BEC tensors have shape
`(N_atoms, 3, 3)` and units of elementary charge. The qNEP exporter performs
the explicit transpose from ZStar's displacement-row convention to GPUMD's
electric-field-row `bec:R:9` convention and preserves unlabeled frames.

qNEP is a concrete compatibility example. It supplies dynamic partial charges,
charge conservation and long-range electrostatics in GPUMD; ZStar supplies
reference structures and optional BEC responses. The checked-in Level 2
benchmark invokes the external GPUMD `nep`/`gpumd` executables, while ZStar
itself does not train qNEP, run GPUMD molecular dynamics, or replace Phonopy or
DYNASOR. In particular,
temperature-dependent polarization, dielectric constants, P--E loops, and
frequency-dependent dielectric functions require a trained model, long MD
trajectories, and external post-processing.

Do not confuse a static partial charge with a BEC, dipole, or polarization.
Absolute BEC values should only be compared when functional, pseudopotential,
basis, k-points, cutoff, units, and atom order are controlled. Otherwise,
compare tensor distributions and trends and report the settings explicitly.
