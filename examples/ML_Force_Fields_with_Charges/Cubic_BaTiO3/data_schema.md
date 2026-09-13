# Sample data schema

`results/sample_dataset/dataset.jsonl` is one JSON object per frame. Required
fields are `frame_id`, `structure_id`, `chemical_symbols`, `cell`, `positions`,
`pbc`, `energy`, `forces`, `stress`, `total_charge`, `temperature`, and
`phase_label`. Response fields are `polarization`, `dipole`,
`born_effective_charges`, and `born_effective_charges_available`.

`born_effective_charges`, when present, has shape `(N_atoms, 3, 3)` and units
of elementary charge. The canonical ZStar convention is displacement/force as
rows and polarization/electric field as columns. The qNEP exporter transposes
this tensor to GPUMD's row-major electric-field/polarization convention.

Each frame also retains calculator, exchange-correlation, pseudopotential,
orbital/basis, k-points, cutoff, source directory/manifest/commit, atom order,
coordinate convention, units, split, and validation status. `frame_id` is the
join key for DFT, BEC, selection, and exported data.

The canonical current result is
`results/qnep_training/dft_only_cubic_173.jsonl` (and its qNEP extxyz export):
169 unique completed DFT frames, 2 BEC-labelled frames, and 167 frames with
explicit missing-BEC state. The older public-source
`results/qnep_export/train_qnep_249_sparse62.xyz` remains a parser fixture and
is excluded from final training. Raw DFT labels are copied without energy
shifts or normalization, and the BEC source and functional remain recorded in
each frame's metadata.
