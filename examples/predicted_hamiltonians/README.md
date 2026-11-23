# Hamiltonian predictions and polarization

The examples connect HamGNN, DeepH, NextHAM, and Hot-Ham predictions to ZStar and
PYATB. The [input guide](../../docs/predicted_hamiltonians.md) describes
how to convert a new prediction and match its orbital basis.

- [hBN with HamGNN and DeepH](hbn/). Compute the nitrogen Born effective
  charge from two test displacements. This case includes the PYATB
  matrices and outputs for both predictions and both ABACUS controls.
- [64-atom silicon with NextHAM](silicon_nextham/). Check the polarization
  of the predicted and initial spinor matrices against the zero branch.
  This case includes the input template and solver results. The full
  matrix inputs are supplied separately for a PYATB replay.
- [hBN with Hot-Ham](hbn_hotham/). Check a real prediction against the
  original ABACUS overlap, inspect the sampled gap, and replay the
  insulating reference Hamiltonian exported by Hot-Ham.
