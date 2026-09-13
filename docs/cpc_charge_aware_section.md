# CPC manuscript insertion (scope-limited)

## Compatibility with charge-aware machine-learning force fields

ZStar also provides a reference-data workflow for charge-aware machine-learning
force fields. The controlled cubic-BaTiO3 demonstration uses 167 unique,
completed ABACUS/PBEsol DFT frames: 117 primitive frames and 50 completed
2x2x2 frames. Twenty-one frames carry BEC tensors (19 primitive and two
representative 40-atom frames); the other 146 frames remain explicitly
unlabeled rather than being represented by zero tensors. The finite-displacement SCF outputs are collected verbatim,
with no energy shifts or normalization, and exported together with structural
and mechanical data in a qNEP-compatible extended-XYZ format. DeepMD
`deepmd/npy` and common MACE extended-XYZ datasets can be used as external
sources for the same representative-structure selection; the subsequent
DFT/BEC workflow is shared. qNEP is used only as a practical compatibility
example. ZStar does not train a qNEP model or perform GPUMD molecular dynamics;
temperature-dependent polarization and dielectric-response simulations remain
external applications.

The public excerpt provides phase labels but no trustworthy per-frame MD
temperature metadata, so the checked-in compatibility result does not fabricate
temperatures or claim the qNEP Figure 5 temperature sweep.

The finite-displacement SCFs already required by the BEC workflow also provide
energy/force-only support rows. ZStar can retain the reference and completed
displacement members with a `parent_frame_id` and explicit missing BEC flag;
these correlated rows are split by parent and are kept separate from the
qNEP paper's r2SCAN force pool when the SCF labels use the PBEsol baseline.

The downstream evidence is a pair of cubic-BaTiO₃ harmonic phonon overlays in
Fig. d. One plot compares DFT and qNEP without NAC; the other compares DFT
and qNEP with NAC, both on the same Γ–X–M–Γ–R–X path. The no-NAC plot
isolates the short-range force-field contribution, while the +NAC plot shows
the final BEC-corrected result. The within-method no-NAC to +NAC shift remains
available in the sidecar as an explicit NAC diagnostic. The cost-capped
qNEP run is evaluated by GPUMD finite-displacement forces and BEC dumps;
Phonopy applies NAC using the qNEP BEC and the DFT electronic dielectric
scalar. These values are reported only as small-model compatibility
diagnostics, not as production fitted-model accuracy.

The included result is not a reproduction of qNEP Figure 5. A complete
Figure 5-style validation would additionally require a converged qNEP model,
GPU MD trajectories spanning the rhombohedral, orthorhombic, tetragonal, and
cubic regimes, and GPUMD/Phonopy/DYNASOR post-processing.

For reproducibility and cost control, the reported model is explicitly a
10,000-generation, one-A30 compatibility run. Its held-out energy, force, and
BEC MAEs are 0.0288 eV/atom, 0.2779 eV/A, and 0.0727 e, respectively; the
force metric is reported as-is and is not presented as production qNEP
accuracy.
