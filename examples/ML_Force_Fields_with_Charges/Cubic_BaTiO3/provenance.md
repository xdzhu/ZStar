# Provenance

* Scientific reference: Fan et al., JCTC 22, 4787 (2026), DOI
  [10.1021/acs.jctc.6c00146](https://doi.org/10.1021/acs.jctc.6c00146).
* Supporting Information: [FanTanBer26.pdf](https://materialsmodeling.org/assets/publications/FanTanBer26.pdf).
* Public models/data: [Zenodo 10.5281/zenodo.18335947](https://doi.org/10.5281/zenodo.18335947).
  The repository stores no full qNEP dataset or model; `run/manifest.example.yaml`
  records URLs and checksums for optional downloads.
* Format reference: [GPUMD train.xyz](https://gpumd.org/nep/input_files/train_test_xyz.html)
  and [charge_mode](https://gpumd.org/nep/input_parameters/charge_mode.html).
* NEP method: Fan et al., Phys. Rev. B 104, 104309 (2021), DOI
  [10.1103/PhysRevB.104.104309](https://doi.org/10.1103/PhysRevB.104.104309).
* GPUMD implementation: Fan et al., J. Chem. Phys. 157, 114801 (2022), DOI
  [10.1063/5.0106617](https://doi.org/10.1063/5.0106617).
* Phonopy: Togo and Tanaka, Scripta Materialia 108, 1--5 (2015), DOI
  [10.1016/j.scriptamat.2015.07.021](https://doi.org/10.1016/j.scriptamat.2015.07.021).
* DYNASOR: Fransson et al., Advanced Theory and Simulations 4, 2000240 (2021), DOI
  [10.1002/adts.202000240](https://doi.org/10.1002/adts.202000240).
* Panel (d) baseline: the existing ZStar cubic-BaTiO₃ ABACUS/PBEsol
  `phonon_spectrum/results` archive, including its BORN and FORCE_SETS files.
  The primary diagnostic is a four-way overlay (DFT without/with NAC and
  qNEP without/with NAC) on the same Γ–X–M–Γ–R–X path. The no-NAC pair
  isolates short-range force-field error; the within-method NAC shift isolates
  the additional BEC/NAC effect. The candidate is the DFT-only, small cubic
  qNEP model trained from the provenance-gated 167-frame split under
  `results/qnep_training/`; earlier `cubic_104_*` outputs are invalid audit
  artifacts. The figure is
  rendered as two overlays (without NAC and with NAC), with an accompanying
  four-way sidecar for the NAC increment diagnostic. GPUMD v5.7
  supplies the finite-displacement forces, direct `compute_phonon` output,
  and equilibrium BEC dump; Phonopy applies NAC using
  `sqrt_epsilon_infinity = 2.621561` (the DFT/PBEsol electronic dielectric
  scalar). The result is a compatibility benchmark, not a claim that ZStar
  itself trains qNEP or performs GPUMD molecular dynamics. The audited qNEP
  run was limited to one NVIDIA A30 and 10,000 generations (about 15 minutes);
  held-out MAEs are 0.0288 eV/atom (energy), 0.2779 eV/A (force), and 0.0727 e
  (BEC). No long training or finite-temperature MD was run for this CPC
  example.
  The authoritative current training input is
  `results/qnep_training/dft_only_cubic_corrected_becpair_20260914/dataset.jsonl`
  (167 unique completed DFT-only cubic frames, 21 BEC labels). The compact
  two-frame Wuzhen response archive has SHA256
  `C52114E6DE4B922293E5947CC646BA0B46E62322D9805FB55D790C4AD55B6877` and is
  intentionally kept outside the repository. The older public-source 249-frame
  export described below is retained only as an interface fixture and is
  excluded from the current model and phonon evidence.
* The optional model checksum is MD5
  `1235b3258b73aaf468f85fd1c7c02035` for
  `qnep-mode1-BaTiO-R2SCAN.txt`; the corresponding 1832-frame public reference
  structure archive has MD5 `2535112ce16d8fba1a2be5eb3f441b2f`. Neither file is
  committed to this repository.
* The sample structures are generated for interface testing and are not DFT
  results. `calculator: synthetic` is deliberate. Replace it with ABACUS or
  another calculator only when all settings and source manifests are recorded.
* `results/sample_dataset/qnep_bto_force_pool250.jsonl` is the 250-row excerpt
  selected from the public 1832-frame qNEP archive with the checked-in selector
  and fixed seed. The canonical `results/qnep_export/train_qnep_249_sparse62.xyz`
  retains that force pool, removes duplicate geometries, and merges 62 BEC
  tensors from 65 completed Wuzhen parent families. Public force/energy rows
  and PBEsol BEC labels are intentionally recorded as separate provenance
  channels; this is a qNEP-compatible mixed-label benchmark, not a strict
  reproduction of the published qNEP training set.
* Wuzhen DFT gate: ABACUS v3.10.0LTS-intelmpi2025 was run in user scratch with
  the same Ba/Ti/O UPF files, numerical orbitals, PBEsol, 100 Ry, LCAO/genelpa,
  `kspacing 0.1` in INPUT, and the existing SCF threshold. ABACUS therefore
  derives the KPT mesh from each cell; the primitive-cell result happens to
  correspond to the familiar Gamma 9x9x9 mesh, but this is not imposed on
  supercells. Job `44122075`
  used 32 MPI x 1 OMP and completed in 134 s; its `OUT.POLAR` sparse matrices
  are not copied into the repository. A reduced no-move PYATB run subsequently
  completed as job `44122813` and produced the expected cubic
  `polarization.dat` (zero branch, 2.019939 C/m² quantum). This verifies the
  ABACUS→PYATB interface. Finite-displacement pilot job `44124489` then
  completed three reduced displacements and one `(5,3,3)` cubic BEC tensor;
  it was collected with `zstar deal --pyatb --bec-only` because this pilot did
  not request the optical/static-dielectric output. The real 50--100-frame BEC
  campaign completed with 65 parent families and 612 reusable force-only SCF
  rows. Frames 13 and 564 remain explicitly unlabeled because their response
  families were incomplete; no zero tensors were inserted. The first
  array (`44126564`) was canceled after
  detecting that a fixed pilot PYATB cell would mismatch distorted frames;
  authoritative rerun `44130012` injects each frame cell from
  `phonopy_disp.yaml` before PYATB and reuses completed ABACUS displacement
  outputs. Dependent array `44132624` covers 17 additional primitive frames.
  The final MPI recovery array `44212769` completed frames 565 and 567 on
  healthy nodes after quarantining `j10r2n12`. ABACUS species blocks are
  canonicalized as Ba/Ti/O; the collector
  explicitly reorders labeled BEC tensors back to each source frame's atom
  order and records that permutation in metadata. Wuzhen is Slurm (22.05); the site
  `qsub/qstat` commands are only a PBS compatibility wrapper. Production
  submissions use native `sbatch`/`squeue`.
