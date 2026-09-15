# Charge-aware frame schema

The canonical ZStar record is JSONL.  A frame has a stable `frame_id` and
contains `chemical_symbols`, `cell`, Cartesian `positions`, `pbc`,
`total_charge`, `energy`, `forces`, optional `stress`, `temperature`,
`phase_label`, provenance fields, and units.

Optional BEC data use:

```text
born_effective_charges: (N_atoms, 3, 3) tensor in e
born_effective_charges_available: true | false
```

`false` means the BEC is missing.  A zero tensor must never encode absence.
The record must also preserve atom order and the tensor coordinate convention.
For qNEP output, ZStar writes BEC only on labelled frames as `bec:R:9` and
transposes the canonical ZStar convention to the qNEP component convention.

`zstar qnep export` supports a sparse parent annotation: phase information is
inherited by children such as `PARENT::disp-001`, while BEC is attached only to
`PARENT::0.no-move`.  All such displaced SCF frames remain valid E/F samples.
