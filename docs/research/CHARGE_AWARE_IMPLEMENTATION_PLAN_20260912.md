# Charge-aware MLFF compatibility implementation plan (2026-09-12)

The requirement-by-requirement status is maintained in
`CHARGE_AWARE_COMPLETION_AUDIT_20260912.md`; this file remains the execution
record for the active Wuzhen campaign.

## Scientific target

The CPC example is a capability demonstration, not a qNEP application paper.
The main downstream result is a cubic-BaTiO3 harmonic phonon overlay:

1. existing ABACUS/PBEsol `with NAC` spectrum as the DFT baseline;
2. qNEP-compatible finite-displacement force constants with a clearly defined
   NAC protocol as the comparison.

The qNEP Figure 5 finite-temperature MD panels remain outside the required CPC
scope. They must not be claimed unless a trained model, long GPU trajectories,
and all response post-processing have actually been completed.

## Priority order

1. **Freeze and audit**: preserve the current branch, dirty user changes,
   existing cubic-BTO DFT/NAC results, and test baseline.
2. **Data interface**: support a controlled 200--500-frame force-field pool,
   explicit sparse BEC labels for roughly 50--100 frames, temperature/phase
   stratification, manifests, and qNEP-compatible export.
3. **External dataset bridge**: read standard DeepMD `deepmd/npy` datasets and
   generic MACE/ASE extended XYZ without requiring `dpdata`; optionally
   normalize labelled ABACUS `STRU`/`OUT.*` directories through `dpdata`, while
   keeping temperature and phase metadata explicit.
4. **DFT/BEC production**: use Wuzhen scratch space and a reviewed
   `32 MPI x 1 OMP` request for selected structures only. The one-frame
   BEC-only pilot is now complete; the next gate is a controlled primitive-cell
   campaign before any larger submission. Every complete finite-displacement
   SCF is also a reusable energy/force support row; the collector exports these
   rows separately with parent/displacement provenance and explicit missing BEC.
   A Python-3.6-compatible compact archive helper is available for moving only
   final force/energy blocks and PYATB polarization outputs off Wuzhen.
5. **Phonon/NAC Level 2**: generate identical finite-displacement structures,
   run qNEP/GPUMD if available, construct NAC without double counting, and
   compare against the existing DFT baseline.
6. **Documentation**: add the CPC compatibility paragraph and example results;
   explicitly label qNEP/GPUMD as external software.

## Wuzhen environment gate

The `ssh wz` login reached `login03`/`login04` as `iai806`. The default user
Python is incomplete for PYATB, so an isolated Python 3.11 environment is
being used under the user work area. The cluster ABACUS installation is now
located at `/work/home/iai806/apprepo/abacus/v3.10.0LTS-intelmpi2025/app/bin/abacus`;
the exact repository BaTiO3 assets were staged and the one-frame smoke job
`44122075` completed with `32 MPI x 1 OMP`. The resulting `OUT.POLAR` sparse
matrices passed the no-move PYATB gate, and job `44124489` completed a
three-displacement cubic BEC-only pilot. No shared environment was modified.

For this CPC compatibility figure, any new DFT/BEC campaign must reuse the
existing cubic-BTO baseline's pseudopotential, orbital/basis, k-points, cutoff,
functional, coordinate convention, and atom order. The qNEP paper's r2SCAN
energy/force/virial plus PBEsol BEC mixture is a separate reference setup and
must not be silently substituted into this data-interface demonstration.

## Resource and provenance rules

- Use a user-owned scratch directory, not the repository or shared examples.
- Submit only selected DFT/BEC frames; preserve frame IDs and source hashes.
- Record job ID, partition/queue, MPI/OMP layout, ABACUS version, functional,
  pseudopotential, orbital, k-points, cutoff, wall time, and output checksums.
- Do not commit raw DFT outputs, full DeepMD datasets, qNEP official archives,
  or GPU caches.
- The current implementation includes Level 1, DeepMD/MACE-style input bridges,
  a verified one-frame Wuzhen BEC-only pilot, and a Level 2 qNEP/GPUMD
  finite-displacement/NAC smoke result. It does not include a finite-temperature
  qNEP MD validation. The first native Slurm submission `44126564` was
  canceled after detecting that a fixed pilot PYATB cell would mismatch
  distorted frames.
  The corrected native-Slurm array `44130012` injects each frame's own cell
  and reuses completed ABACUS displacement outputs where available; it is the
  authoritative run. Frames 12, 14, 15, 16, 17, 18, and 523 are the seven
  completed corrected frames and have passed local BEC-only collection. A dependent
  native-Slurm add-on (`44132624`) covers 17 more primitive candidates, giving
  a practical 67-frame sparse-BEC campaign; 33 parent families have currently
  passed the local collection gate and campaign-level coverage is not yet final.
