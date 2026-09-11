# Experimental tetragonal BaTiO3 electromechanical smoke

This directory is a v2 research fixture for a non-centrosymmetric tetragonal
BaTiO3 structure. It is not a validated material benchmark or a stable CLI
example. The input structure is intentionally kept under `inputs/`; ABACUS
outputs and large pseudopotential/orbital files are not committed here.

The structure is used only to test the reference → Berry triplet → branch
matching → raw piezoelectric fit chain. Proper/improper corrections, relaxed-ion
contributions, convergence extrapolation, and independent-backend comparison
remain required before any scientific claim.
