# qNEP charge-aware compatibility research record

Date: 2026-09-12  
Repository freeze reference: `6748e50` (`Add paired-bar efficiency figure to manuals`)  
Development branch: `codex/qnep-charge-aware-compatibility`

This record is the scope gate for the ZStar compatibility example. It is not a
claim that ZStar implements qNEP, GPUMD, Calorine, or DYNASOR.

## Sources checked

* Fan et al., *qNEP: A Highly Efficient Neuroevolution Potential with Dynamic
  Charges for Large-Scale Atomistic Simulations*, JCTC 22, 4787 (2026), DOI
  [10.1021/acs.jctc.6c00146](https://doi.org/10.1021/acs.jctc.6c00146).
* Supporting Information, [FanTanBer26.pdf](https://materialsmodeling.org/assets/publications/FanTanBer26.pdf), especially SN8--SN11 and Eqs. 3--4, 30--33.
* qNEP models/reference data, Zenodo DOI
  [10.5281/zenodo.18335947](https://doi.org/10.5281/zenodo.18335947). The record
  reports 53.6 GB total volume; the BaTiO3 model is 98.3 kB and the BaTiO3
  reference XYZ is 8.1 MB (MD5 `1235b3258b73aaf468f85fd1c7c02035` for the
  mode-1 model and `2535112ce16d8fba1a2be5eb3f441b2f` for the reference XYZ).
* GPUMD `train.xyz` specification,
  [train.xyz and test.xyz](https://gpumd.org/nep/input_files/train_test_xyz.html),
  and [`charge_mode`](https://gpumd.org/nep/input_parameters/charge_mode.html).

## Verified qNEP data and physics requirements

1. qNEP learns environment-dependent latent partial charges. These are not
   static Bader/Hirshfeld-like partial charges. The model applies a learned
   high-frequency dielectric screening parameter and a total-charge correction.
2. A BEC tensor is the derivative of polarization with respect to an atomic
   displacement. It is therefore not the same physical quantity as a partial
   charge, a dipole, or a polarization vector. qNEP's polarization is built
   from BECs and displacements relative to a cubic reference for BaTiO3,
   \(P_\alpha=V^{-1}\sum_i\sum_\beta Z_{i,\alpha\beta}u_{i\beta}\).
3. GPUMD accepts `species:S:1`, `pos:R:3`, `force:R:3`, and optional
   `bec:R:9`; energy is total eV/cell, forces are eV/Angstrom, virials are eV,
   and BEC is in elementary charge. BEC is explicitly optional and may be
   present for only some structures. A frame without BEC is an unlabeled frame,
   not a nine-component zero target.
4. qNEP's training loss contains energy, force, virial, optional BEC, and total
   charge terms. Energy/force/virial labels remain the ordinary potential-data
   labels. BEC labels supervise the response branch; total charge enforces
   charge conservation. The paper reports that about 64 BaTiO3 structures
   (less than 4% of the full set) were enough for BEC prediction convergence.
5. BaTiO3 uses 639 initial structures plus 1193 additional 20-atom
   \(\sqrt2\times\sqrt2\times2\) supercell structures, for 1832 structures and
   36,540 atoms total. The additional structures span 50--600 K and sample the
   rhombohedral, orthorhombic, tetragonal, and cubic phases. The initial set
   also contains relaxed structures, rattles, ferroelectric-mode displacements,
   and active-learning structures (including hexagonal variants). Energies,
   forces, and virials use r2SCAN; BECs use DFPT/PBEsol.

## Figure 5 and Figure 6 workflow boundaries

Figure 5 is a full qNEP/GPUMD finite-temperature MD application, not a file
format demonstration. The paper uses a 40,000-atom 20x20x20 cell, 100 ps NPT
equilibration at 500 K, 45 ns cooling from 500 to 50 K at 10 K/ns, then heating
at the same rate. One hundred trajectory structures are used for lattice
parameters, polarization, and dielectric response. Static dielectric response
uses zero-field and 1 mV/Angstrom field MD; P--E loops sweep +/-0.2 V/nm over
2 ns (500 MHz); the imaginary dielectric function comes from the Fourier
transform of the \u27e8Pdot(0)Pdot(t)\u27e9 ACF and the real part from a
Kramers--Kronig transform. The reported dielectric response is ionic/
vibrational only, unlike experiments that also include slower extrinsic terms.

Figure 6 separates three tools: harmonic phonons are evaluated with Phonopy
on 4x4x4 (320 atom) supercells, NAC/LO--TO splitting uses BEC information,
and finite-temperature spectral energy density is computed from a 233,280-atom
qNEP/NEP NVE trajectory and post-processed by DYNASOR. The LO--TO splitting in
the qNEP MD spectrum comes from qNEP long-range electrostatics; it is not a
ZStar-only result.

## ZStar scope decision

The current CPC software paper should include only a short section titled
**Compatibility with charge-aware machine-learning force fields**. ZStar can
select temperature/phase-resolved structures from JSONL, DeepMD `deepmd/npy`,
and generic ASE/MACE-style extended XYZ sources, run its existing BEC workflow,
preserve sparse BEC availability, validate provenance and tensor conventions,
and export GPUMD/qNEP-compatible extended XYZ. ZStar does not implement qNEP
training or GPUMD MD; the external compatibility benchmark does invoke the
official GPUMD `nep` executable to train a deliberately small cubic-only model
and then uses GPUMD/Phonopy for the harmonic phonon/NAC check. The BTO example
is therefore called **qNEP-compatible response-data workflow** plus a Level 2
small-model harmonic phonon/NAC result. It is not a reproduction of Figure 5
or a production qNEP model.

Absolute BEC values from an independent ABACUS/PBEsol setup are not directly
comparable with the qNEP reference values if pseudopotentials, basis, k-points,
cutoffs, or functionals differ. Such a result is described as an independent
ZStar reference label; only tensor distributions, trends, and explicitly
matched RMSE/MAE comparisons are meaningful.

## Environment check

The local ZStar suite is `425 passed` (2026-09-13). G1 is reachable and has
four NVIDIA A30 GPUs (24,576 MiB each), driver 545.23.06, CUDA 12.3, GCC 8.5,
CMake 4.0.2, Open MPI 5.0.8, and Python 3.12.11. GPUMD v5.7 was built in
user scratch; a cubic-only 83/21 qNEP training run (5,000 generations) and
GPUMD `compute_phonon`/force/BEC run completed on GPU 0. The trained model and
small logs are recorded under the example results; the official 53.6 GB model
was not copied into the repository. The configured `ssh -J G1 G2` probe did not return within the
connection timeout, so no G2 capability is claimed. Wuzhen provides ABACUS
v3.10.0LTS-intelmpi2025 and the matching repository BaTiO3 assets. Job
`44122075` completed the exact baseline ABACUS smoke (32 MPI x 1 OMP), and
PYATB job `44122813` completed a no-move Berry-polarization smoke. Slurm job
`44124489` then completed a manually staged four-stage finite-displacement
pilot and a validated one-frame `(5,3,3)` BEC-only tensor (acoustic-sum-rule
residual `2.7e-15 e`). The first native array (`44126564`) was canceled after
its fixed pilot PYATB cell was found inconsistent with distorted frames. The
authoritative native Slurm rerun is `44130012`, which injects each frame cell
from `phonopy_disp.yaml` and reuses completed ABACUS displacement outputs for
50 primitive-cell candidates. A source audit shows that the public primitive
archive can supply at most 13 rhombohedral and 14 orthorhombic structures;
cubic and tetragonal can each reach 20 when displacement snapshots are
admitted. We therefore queued dependent native array `44132624` for 17
additional primitive candidates, giving a practical 67-frame sparse-BEC
campaign (13/14/20/20 by phase) without duplicate geometries or 120-atom
supercells. Frames 12, 14, 15, 16, 17, 18, and 523 are the first seven
completed corrected frames; their BEC tensors passed local BEC-only
postprocessing and atom-order provenance checks. The recovery diagnostic for
frame 566, the single-frame recovery for frame 569, and add-on frames 79, 34,
and 95 have also completed and passed the same checks. Together with the
19 compacted families from the initial batch, 51 parent frames are now
validated. The remaining array tasks are still running, so the 51/67
result is an intermediate artifact rather than final campaign coverage. The
late array tasks that hit the Wuzhen Intel-MPI topology failure are being
recovered separately with `I_MPI_FABRICS=ofi`; no successful frame is rerun.

The collector also reuses the SCF work already paid for by each accepted BEC
family. The initial seven complete local families produced 62 PBEsol
energy/force-only rows (reference plus completed displacements); the 51 compacted
validated families currently produce 432 such rows. Every row has an explicit missing BEC flag,
parent-frame link, and displacement metadata. This auxiliary label
family is kept separate from the public qNEP r2SCAN force pool; it is not
silently mixed into qNEP training data.

## Freeze and pre-existing workspace state

The branch was created from commit `6748e50`; the worktree already contained
user changes (README/manual updates, phonon/spectroscopy code and tests, and
an existing cubic-BaTiO3 phonon example). Those edits were not reset or
overwritten. No standalone CPC manuscript source was present in the repository;
the proposed insertion is therefore recorded as `docs/cpc_charge_aware_section.md`
rather than silently editing an unavailable manuscript. Existing manual and
example content remains in place, with the new charge-aware section added as a
separate page and a new small example under
`examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3`.

## Final collection update (2026-09-13)

The intermediate 51/67 note above is superseded by the completed frame-level
gate. Arrays `44206174`, `44206175`, `44206275`, and final recovery `44212769`
yielded 65 complete parent families and 612 reusable SCF energy/force rows;
source parents 13, 560, and 564 remain explicitly unlabeled. The canonical
export contains 249 unique force-pool structures and 62 BEC labels, passes the
charge-aware validator and qNEP parser, and is recorded under
`examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/results/`.

After the compatibility changes, the full local suite reports `424 passed`
(2026-09-12); this includes sparse-BEC, DeepMD/MACE-style adapter, phonon
comparison, and round-trip tests. The checked-in phonon overlay is generated
from the independent qNEP smoke outputs and is not a temperature-dependent MD
result.
