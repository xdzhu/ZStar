# qNEP high-quality training plan for the cubic BaTiO3 example

## Data audit before training

The current provenance-gated cubic-only set contains 167 completed ABACUS
frames:

| subset | frames | energy/force | stress | BEC |
| --- | ---: | ---: | ---: | ---: |
| primitive 5-atom rows | 117 | 117 | 0 | 19 |
| 2x2x2 40-atom rows | 50 | 50 | 50 | 2 |
| total | 167 | 167 | 50 | 21 |

The 40-atom subset consists of 46 perturbation/supplement rows plus four
already-computed phonon rows (`phonon_equilibrium` and
`phonon_disp_001..003`). All 146 unlabeled frames retain an explicit missing
BEC state. The data use the same PBEsol, pseudopotential/orbital baseline and
`kspacing=0.1`; no energy shift is applied. The set is appropriate for a
cubic-phase compatibility/phonon benchmark, but it is much smaller and much
sparser in BEC/stress coverage than the published qNEP BTO reference set.

## What the official recipe says

The qNEP Supporting Information, Supplementary Note 8, reports a BaTiO3
reference set of 1832 structures (1193 with BECs) and a single 500,000-SNES-
generation training run with `cutoff 6 4`, `n_max 8 6`, `l_max 4 0`, `neuron 40`,
`lambda_e=lambda_f=1`, `lambda_v=lambda_q=lambda_Z=0.1`. This is the reference
recipe, not a guarantee that the present 167-frame set can reach the same
accuracy. The GPUMD documentation defines `generation` as the SNES iteration
count and recommends a batch of roughly 100--1000 for diverse data; for this
134-frame training split, a full batch of 134 is the least noisy choice.

## Cost-controlled staged run

1. A 5,000-generation timing test was run on G1 with the official descriptor
   and loss settings. One A30 took 526 s; four A30s took 164 s (3.2x wall-time
   speedup). All four GPUs remained healthy.
2. The first bounded high-quality candidate is now running on four A30s with
   `generation=100000`, `batch=134`, and `output_interval=1000`. It is a fresh
   run on the leakage-safe 134/33 train/test split.
3. At 100k, copy the checkpoint and evaluate held-out E/F/BEC. Continue to
   300k only if the force and BEC errors improve materially and the loss has
   not plateaued. Continue to 500k only if the 300k checkpoint improves the
   held-out metrics and the 222 phonon overlay becomes physically plausible.
4. Estimated wall times from the measured 4-GPU rate are approximately 55 min
   (100k), 2.7 h (300k), and 4.6 h (500k), with a practical 20--30% margin. No
   stage is submitted automatically beyond the current 100k cap.

The restart file must be preserved when extending a stage; GPUMD checks that
descriptor and architecture keywords match before resuming. If the force error
remains near the current 0.25--0.28 eV/A after 100k, more generations alone
are not a justified use of GPU time: the next action is to improve the data
coverage (especially stresses and representative BECs) or adjust loss weights,
then rerun a short diagnostic.

## Acceptance language

Even a successful 500k run on this small set should be called a
“cubic-BaTiO3 qNEP compatibility benchmark”. It must not be described as a
reproduction of the published qNEP model or Figure 5, because the present set
does not cover all four phases/temperatures and no finite-temperature MD is
planned for the CPC example.

References: [qNEP Supporting Information](https://materialsmodeling.org/assets/publications/FanTanBer26.pdf),
[GPUMD `nep.in` documentation](https://gpumd.org/nep/input_files/nep_in.html),
[GPUMD `charge_mode` documentation](https://gpumd.org/nep/input_parameters/charge_mode.html),
and [the public qNEP Zenodo record](https://zenodo.org/records/18335947).

## Independent G2 500k candidate (started 2026-09-14)

At the user's request, an independent full 500,000-generation run was started
on G2 while the G1 100k diagnostic run remains untouched. G2 GPUs 4 and 5 are
NVIDIA A30 (24,576 MiB each) and were idle at launch; GPUs 0--3 were occupied
by unrelated processes and were not used. The run directory is
`/home/zhuxd/zstar-qnep-compat/dft_only_cubic_corrected_becpair_20260914/official_bto_hq_500k_g2`,
with PID 2658926 and the same 134/33 train/test split and official BTO
hyperparameters. The source data are copied byte-for-byte (SHA256 is recorded
in `official_bto_hq_500k_g2_run_20260914.json`); no energy shift or label
rewrite was applied.

The G2 node did not expose the CUDA 12.3 cuBLAS/cuFFT libraries required by the
existing GPUMD 5.7 binary. The required runtime libraries were copied into the
user's isolated `cuda12.3-runtime` directory; the shared system environment was
not changed. The first observed rate was approximately 1,000 generations per
minute on two A30 GPUs, so wall time is expected to be roughly 8--10 hours (to
be refined from later checkpoints). This parallel run is an explicitly
requested candidate, not evidence that the staged 100k -> 300k stopping gate
has already been passed.

## 100k checkpoint audit

The G1 four-GPU run completed 100,000 generations and was evaluated on the
held-out 33-frame split. The resulting errors are 0.0183 eV/atom energy MAE,
0.2921 eV/A force MAE, and 0.1040 e BEC MAE (BEC evaluated on 85 labelled atom
rows). The corresponding 222 phonon overlay gives 6.53 THz MAE without NAC and
5.95 THz MAE with NAC against the archived DFT/PBEsol reference. These values
are not an improvement over the 5,000-generation timing candidate (force MAE
0.2540 eV/A, BEC MAE 0.0813 e), so the staged gate for automatically extending
the G1 checkpoint to 300k is not satisfied. The 100k model and both NAC
overlays are retained as an audit result; they are not presented as a
production-quality force field.

The G2 run subsequently crossed 100k. Its independent 100k checkpoint gives
0.01627 eV/atom energy MAE, 0.28881 eV/A force MAE, and 0.10216 e BEC MAE on
the same held-out split. This does not materially improve the G1 100k result;
the checkpoint is therefore retained for convergence tracking only, while the
explicitly requested G2 run continues to 500k.

The independent G2 run reached an interim 50k checkpoint while continuing
towards 500k. Its held-out errors were 0.01864 eV/atom (energy), 0.27303 eV/A
(force), and 0.05606 e (BEC). BEC improved relative to the G1 100k result, but
the force error is still well above the ~0.10 eV/A target and the value is not
yet a final-model assessment. The checkpoint is recorded under
`official_bto_hq_500k_g2_checkpoint50k/`; the G2 process remains active.
