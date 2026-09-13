# qNEP/GPUMD environment audit

* G1 (`ssh G1`) responded on 2026-09-12. It has four NVIDIA A30 GPUs,
  24,576 MiB each, driver 545.23.06, CUDA 12.3, GCC/G++ 8.5, CMake 4.0.2,
  Open MPI 5.0.8, Python 3.12.11, NumPy 1.26.4, SciPy 1.15.2 and Matplotlib
  3.10.3. At the check time each GPU reported about 4 MiB used.
* The checked G1 Python environment did not contain GPUMD/qNEP, Phonopy,
  Calorine, ZStar, ABACUS, or PYATB. No shared environment was modified.
* A clone/build was attempted only below `/home/zhuxd/zstar-qnep-compat`.
  The public GitHub clone did not return within the connection timeout and was
  terminated; no executable or model was produced. The local marker was
  `INSTALL_BLOCKED_network.txt`.
* `ssh -J G1 G2 hostname` did not return within the connection timeout, so G2
  is not treated as available and no G2 job was submitted.
* On G1, the public GPUMD v5.7 release was built below
  `/home/zhuxd/gpumd-qnep-v5.7/GPUMD-5.7` with the bundled CUDA compiler and
  `make -j4`; both `gpumd` and `nep` compiled successfully. The official
  qNEP mode-1 BaTiO3 model was staged only in user scratch as
  `/home/zhuxd/qnep-bto/qnep-mode1-BaTiO-R2SCAN.txt` (MD5
  `1235b3258b73aaf468f85fd1c7c02035`).
* A controlled GPU calculation used only G1 GPU 0
  (`CUDA_VISIBLE_DEVICES=0`) to train a cubic-only qNEP mode-1 benchmark
  (`83/21` train/test frames, 5,000 generations) and to run GPUMD
  `compute_phonon` on the trained model. The documented 8×8×8 cell was used
  for the direct force-constant calculation; a compact 40-atom displacement
  archive supplied the Phonopy NAC force set and BEC dump. Logs and outputs
  are recorded under `results/qnep_training/cubic_104_seed20260913/`.
  This is a Level 2 small-model compatibility benchmark, not production MD or
  Figure 5 finite-temperature validation.

## Wuzhen (`ssh wz`)

The login host is `login03`/`login04` and the user account is `iai806`. The
default user Anaconda interpreter is old and does not provide the complete
PYATB stack, so isolated Python 3.11 environments are kept under the user
work area. The production-compatible `pyatb-systemclean` environment uses the
site NumPy/Matplotlib pair plus user-space ASE, mpi4py, and PYATB 1.1.2; the
earlier `pyatb-venv` NumPy-2 trial is not used. No shared environment was
modified.

The cluster ABACUS installation was located and loaded with
`compiler/gcc/9.3.0`, `compiler/intel/2021.3.0`, `mpi/intelmpi/2021.3.0`, and
`mathlib/libxc/4.3.4/intel`. The executable is
`/work/home/iai806/apprepo/abacus/v3.10.0LTS-intelmpi2025/app/bin/abacus`.
The exact cubic-BaTiO3 baseline assets from this repository were staged in
user scratch (Ba/Ti/O UPF files and numerical orbitals), and a one-frame
ABACUS smoke job completed as job `44122075` on node `j10r4n15` using
`32 MPI x 1 OMP`. It used PBEsol, 100 Ry, LCAO/genelpa, Gamma 9x9x9 and
`scf_thr=1e-7`; wall time was 134 s and `OUT.POLAR` contained the sparse H/S/rR
matrices required by PYATB. Raw output remains in user scratch and is not
committed.

The no-move PYATB Berry-polarization smoke subsequently completed as job
`44122813` after reducing the input to the polarization block (the first
launcher attempt exposed a site `srun` route issue and was cancelled by the
owner). `Out/Polarization/polarization.dat` was produced with zero polarization
within the cubic reference branch and a polarization quantum of 2.019939 C/m²
in each Cartesian direction. Slurm job `44124489` then completed the three
reduced finite-displacement PYATB stages and produced the one-frame BEC-only
pilot; the tensor obeys the acoustic sum rule to `2.7e-15 e`. At that initial
smoke checkpoint the planned 50--100-frame campaign was still pending;
production MD remains future work. The one-rank PYATB run took about 220 s for the 19x19x19 polarization
mesh. The scheduler's existing jobs were not modified.

Final Wuzhen campaign update (2026-09-13): the 50--100-frame gate completed
with 65 parent families and 612 reusable SCF energy/force rows. The final
recovery array `44212769` completed frames 565 and 567 using 32 MPI ranks and
one thread per rank on healthy nodes; `j10r2n12` remains quarantined. Three
source parents (13, 560, 564) were withheld as incomplete. This closes the
data-interface campaign but does not promote the work to finite-temperature
qNEP MD.

Cost-controlled long-training update (2026-09-14): four exploratory 200k
generation runs were initially started on separate A30 GPUs using the fixed
cubic-only interim split.  At approximately 34k generations, the two `n80`
configurations had higher force-test loss than both `n50` configurations, so
their exact GPUMD processes were terminated and their partial `loss.out` and
model files retained.  Only `n50_z01` and `n50_z05` continue.  This is an
interim hyperparameter screen; final training must be rerun once the completed
40-atom BEC annotations are merged, and no partial run is reported as the
final qNEP model.

Final cost-capped compatibility run (2026-09-14): the merged pure-DFT cubic
dataset contains 167 frames (134 train/33 test after family-safe splitting)
and 21 sparse BEC frames (18/3 split). One n50/lambda_z=0.5 qNEP run used
G1 GPU 0 (`CUDA_VISIBLE_DEVICES=0`, one CPU thread) with a 100k-generation
request and an owner watchdog at 10k generations. It completed exactly 10k
generations in about 15 minutes, then released the GPU. Test MAE was
0.0288 eV/atom for energy, 0.278 eV/Angstrom for forces, and 0.0727 e for
the 85 labelled atom rows in the BEC output. This is sufficient for a
workflow/format and phonon compatibility check, not a production qNEP
accuracy claim; no additional long training was submitted.
