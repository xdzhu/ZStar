# Wuzhen ABACUS/PYATB gate (2026-09-12)

This note records the first remote calculation for the charge-aware example.
The remote work directory is `/work/home/iai806/zstar_qnep_compat/abacus_smoke`;
no raw output is copied into the repository.

Wuzhen is a Slurm cluster (Slurm 22.05).  The site also exposes `qsub`/`qstat`
as a PBS-compatible wrapper, but the scheduler-native interface is `sbatch`,
`squeue`, and `sacct`; subsequent production jobs will use `#SBATCH` headers
and the native Slurm commands.  The pilot job listed below was submitted while
the wrapper was being diagnosed and is still a Slurm job underneath.

## ABACUS smoke

* executable: `/work/home/iai806/apprepo/abacus/v3.10.0LTS-intelmpi2025/app/bin/abacus`
* modules: GCC 9.3.0, Intel compiler 2021.3.0, Intel MPI 2021.3.0,
  libxc 4.3.4/intel
* job: `44122075`, queue `wzacnormal`, node `j10r4n15`
* resources: 32 MPI ranks, 1 OpenMP thread per rank
* settings: the existing cubic-BaTiO3 ZStar baseline (PBEsol, LCAO/genelpa,
  100 Ry, `kspacing=0.1` in INPUT, `scf_thr=1e-7`, same Ba/Ti/O UPF and
  numerical-orbital files, same atom order and lattice). The primitive-cell
  result is the familiar Gamma 9x9x9 mesh; supercells use the cell-dependent
  automatic mesh.
* wall time: 134 s; exit status: successful
* output: `OUT.POLAR` with sparse H/S/rR matrices and charge-density restart

This validates that the exact DFT baseline can run on Wuzhen. It is not a BEC
label yet.

## PYATB gate

An isolated Python 3.11 environment contains the public PYATB 1.1.2 wheel,
ASE, and `mpi4py` in user space. A reduced no-move PYATB calculation completed
as job `44122813` against the `OUT.POLAR` matrices and produced
`Out/Polarization/polarization.dat`. The cubic branch is zero within numerical
precision and the polarization quantum is 2.019939 C/m². The first scheduler
launch exposed a site MPI launcher issue (`srun: ROUTE: split_hostlist`); that
job was cancelled by the owner and did not affect other users. The interface
gate is therefore passed for the equilibrium case, but finite-displacement BEC
labels still require a small batch followed by the planned 50--100-frame
campaign. That campaign has since been submitted as native Slurm array
`44130012`; its final coverage is still pending.

The successful PYATB run used one rank and took about 220 s (the 19x19x19
polarization mesh reaches the 800-k-point cap). This runtime is recorded so a
future batch estimate does not confuse a no-move interface test with a cheap
production calculation.

The finite-displacement pilot was Slurm job `44124489` on partition
`wzacnormal`, using 32 MPI ranks and one OpenMP thread. It completed three
symmetry-reduced displacements for one cubic reference frame. The resulting
`(5,3,3)` BEC tensor obeys the acoustic sum rule to `2.7e-15 e` and is stored
as a small validation artifact under the example. Collection used
`zstar deal --dim 3 --pyatb --bec-only`, so no static dielectric or BORN file
was expected. This is a verified BEC-only pilot, not the planned 50--100-frame
campaign.

The controlled primitive-cell campaign has now been prepared from 50
phase-stratified five-atom qNEP-reference structures (12 rhombohedral, 13
orthorhombic, 12 tetragonal, 13 cubic; no temperature metadata was available
in the public XYZ archive). A larger source audit can provide a final
primitive-cell target of 20 rhombohedral, 20 cubic, 20 tetragonal, and 18
orthorhombic frames. The two-frame shortfall is a property of the public
primitive archive, not a missing-label placeholder. Padding with 120-atom
supercells was deliberately not sent to the routine BEC queue because each
would create hundreds of phonopy displacements. The first native Slurm submission (`44126564`) was
canceled after a cell-consistency audit found that a fixed cubic pilot PYATB
template would mismatch distorted frames. The authoritative rerun is native
Slurm array `44130012`, with at most eight concurrent 32-MPI tasks; its driver
injects each frame's cell from `phonopy_disp.yaml` and reuses completed ABACUS
displacement outputs. Its pending/running/
completed state must be audited with `squeue`/`sacct`; submission alone is not
counted as BEC coverage. Frames 12, 14, 15, 16, 17, 18, and 523 have completed and passed
local `zstar deal --bec-only` post-processing, including explicit restoration
of their source Ba/O/O/O/Ti atom order after ABACUS's Ba/Ti/O species-block
order. A dependent native Slurm array `44132624` is queued for 17 additional
primitive candidates and will start only after `44130012` succeeds. The
resulting 67-frame primitive campaign is the practical sparse-BEC target: 20
cubic, 20 tetragonal, 14 orthorhombic, and 13 rhombohedral frames. The
remaining two phase targets cannot be filled from the public primitive source
without fabricating structures or sending 120-atom supercells to a routine
BEC workflow. The collector rejected frame 13 because one reused displacement
log lacked the ABACUS final-time marker; no BEC label was emitted for that
frame.

During the late part of `44130012`, tasks on two nodes failed at Intel-MPI
initialization (`llc_id >= 0`, followed by signal 9), before a usable SCF
result. These are infrastructure failures, not SCF convergence failures.
Recovery arrays `44137536` (19 frames), `44137548` (frame 569), and `44137563`
(17 add-on frames) use the same 32-MPI/1-OMP request with
`I_MPI_FABRICS=ofi` and the user-owned PYATB path. Diagnostic recovery
`44136851` was used first for frame 566; successful tasks are not rerun.

That diagnostic and the first completed recovery tasks subsequently finished
with exit code 0: frame 566 (diagnostic), frame 569 (single-frame recovery),
and frames 79, 34, and 95 (add-on recovery) were compacted and re-read locally.
Together with the 19 compacted families from the initial batch, these outputs
passed the same BEC-only, atom-order, and force-only extraction checks; the
campaign currently has 51 validated parents out of the 67 requested.

## Consistency rule

Any selected DeepMD, MACE, qNEP, or other force-field frame sent to this
workflow must retain its stable frame ID and atom order. New reference labels
must use the existing ZStar cubic-BaTiO3 DFT setup exactly; changing the
functional, pseudopotential, orbital, k mesh, cutoff, or coordinate convention
creates a different reference dataset and must be reported as such.

## Slurm recovery operation (2026-09-13)

The pending addon array `44132624` was found to depend on
`afterok:44130012_*`.  Several elements of the original array had already
failed with exit code `127`, so that dependency could never become satisfied.
The pending array was canceled before it started and resubmitted without the
dead dependency as `44204812` (17 addon frames, at most eight concurrent
32-MPI tasks, `I_MPI_FABRICS=ofi`).  The incomplete primary frames, excluding
the currently running frame 524, were submitted independently as recovery
array `44204753` (12 frames, at most four concurrent 32-MPI tasks, the same
MPI workaround).  No frame is present in both recovery lists, and no running
task writes frame 524.

At the time of resubmission, `44130012_8` was running frame 524.  Its
`0.no-move` and `disp-001` stages had completed; ABACUS was in `disp-002`
(`GE4` in the SCF log), with six displacement stages (`disp-003` through
`disp-008`) still to process after that stage.  The first displacement took
about 10.2 h, so a conservative estimate is roughly 2.5--3 days for the
remaining work if the same per-stage cost persists.  This is intentionally
approximate because frame 524 is much slower than completed frame 523.

## Frame-524 node quarantine and continuation (2026-09-13)

The 10.2 h runtime of frame 524 `disp-001` was confirmed anomalous: the same
`INPUT`/`KPT` and 32-MPI setup completed neighboring frames' displacement
SCFs in roughly 2--4 min, whereas frame 524 spent about 3,560--3,610 s per
SCF iteration on node `j10r2n12`.  That node was also running unrelated MPI
work and showed a high system load.  The original task `44130012_8` was
canceled after preserving the completed `disp-001` output.  A continuation
array `44205343` was submitted for frame 524 with `I_MPI_FABRICS=ofi` and
`--exclude=j10r2n12`; future recovery submissions must keep this node
excluded.  A follow-up inspection showed that the reused `0.no-move` branch
did not initialize BLAS thread limits before launching PYATB; the first
continuation consequently spawned roughly 34 Python threads and was canceled
before any new BEC stage completed.  The batch driver now exports
`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`,
`NUMEXPR_NUM_THREADS=1`, and `MKL_DYNAMIC=FALSE` before either program.  The
corrected continuation is `44205611`, again excluding `j10r2n12` and using
`I_MPI_FABRICS=ofi`; the interrupted PYATB directory was moved aside rather
than overwritten.  The same thread oversubscription was found in both earlier
recovery arrays `44204753` and `44204812`; they were canceled before accepting
new BEC labels, their interrupted `0.no-move/pyatb` directories were backed
up, and corrected replacements `44205767` (primary) and `44205768` (addon)
were submitted with the same thread limits and node exclusion.

The recovery driver was then tightened further: PYATB's polarization module
uses `mpi4py`/`COMM_WORLD` and distributes Berry-phase strings over ranks, so
it is now launched as `mpirun -np 32 pyatb` with one BLAS/OpenMP thread per
rank, matching the `mpirun -np 32 abacus` SCF launch.  The not-yet-started
arrays `44205767` and `44205768` were replaced by MPI-PYATB arrays `44206174`
(primary) and `44206175` (addon), again excluding `j10r2n12`.  The already
running frame-524 continuation `44205611` was later replaced after its
`disp-002` ABACUS stage completed in 149 s on `j11r3n10`; MPI-PYATB
continuation `44206275` now handles frame 524.  A live process audit showed
32 `pyatb` Python ranks on the new job, each using one compute thread,
confirming the intended 32-rank x 1-thread layout.

## Final campaign status (2026-09-13)

The final recovery array `44212769` completed frames 565 and 567 with exit
code 0 on healthy nodes `b10r2n18` and `b10r2n21`. The frame-level collection
gate is closed: 48 primary families and 17 add-on families are complete, while
source parents 13, 560, and 564 remain explicitly unlabeled because their
response families are incomplete. The compact collection yields 612 reusable
PBEsol SCF energy/force rows. The canonical repository export contains 249
unique force-pool structures and 62 nonzero BEC labels; no raw scratch output
or zero-matrix placeholder is used.
