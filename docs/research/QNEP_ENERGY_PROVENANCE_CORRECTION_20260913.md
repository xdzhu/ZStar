# qNEP example energy-provenance correction

The first small qNEP training experiments were discarded.  They combined the
public qNEP force-pool excerpt (5-atom rows near -74 eV) with newly collected
Wuzhen ABACUS/PBEsol rows (5-atom rows near -3729 eV and 40-atom rows near
-29834 eV).  These are different label sources and the resulting energy target
is invalid.  No energy shift or normalization is permitted as a repair.

The completed Wuzhen BEC families already contain the needed SCF energy/force
outputs.  A scheduler-neutral collector was added at
`examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/run/collect_abacus_force_only.py`.
It reads only completed `FINAL_ETOT_IS` and `TOTAL-FORCE` blocks, copies the
values verbatim, and records the source log.  On 2026-09-13 it collected 612
rows from 65 complete parent families.  Two of the 67 candidate directories
remain incomplete (`13` and `564`) and are reported rather than filled with
placeholders.

The final DFT-only cubic training input assembled from these raw rows contains
169 unique frames: 119 primitive 5-atom rows, 50 already completed 2x2x2
40-atom supplement rows, and two sparse primitive BEC labels. Four identical
geometries were removed only after their raw energy/force labels were checked
for agreement. The public qNEP excerpt remains an interface/parser fixture
only; it is not a force or energy source for the final model. Existing raw DFT
directories are reused, not rerun, and the two incomplete families remain
reported as incomplete rather than being resubmitted.
