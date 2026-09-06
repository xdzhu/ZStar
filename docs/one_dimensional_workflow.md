# One-dimensional wires and nanowires

The [Unified spectroscopy tutorial](unified_spectroscopy.md) covers the current
default Raman route. The Sb2S3 case now reuses the BEC matrices; its retained
52-SCF mode-displacement result is the independent control, not an additional
requirement of the Unified workflow.

ZStar uses `dim=1` for a system periodic along one lattice direction. The
production ABACUS + PYATB workflow currently requires that direction to be
Cartesian `z`, with the two nonperiodic cell vectors aligned with `x` and `y`.
Vacuum padding is therefore confined to the transverse cross-section.

## Physical convention

A wire needs a hybrid polarization treatment. The periodic `z` component is a
Berry-phase polarization from PYATB. The localized transverse `x/y` components
are dipole moments integrated from neutral ABACUS charge-density cubes. For an
atomic displacement along `beta`, ZStar assembles the canonical tensor

```text
Z*(beta,alpha) = d p_alpha / d u_beta
```

where rows are atomic displacement/force and columns are polarization/electric
field. The transverse columns come from real-space dipoles and the periodic
column comes from the Berry derivative. The resulting Born effective charge is
in units of `e` and does not depend on the amount of vacuum.

Current PYATB releases evaluate Berry loops along all three axes even for a 1D
periodicity mask. ZStar therefore pads the generated polarization mesh from
`1 x 1 x N` to the minimum valid `2 x 2 x N` grid, records the adjustment in
`zstar_pyatb_polarization_compat.json`, and consumes only the physical `z`
component. This is an upstream compatibility measure, not a transverse Berry
polarization model.

The transverse finite difference also requires a high-precision charge cube.
ZStar writes `out_chg 1 10` for low-dimensional polarization/BEC stages; the
second value avoids the coarse default rounding from dominating the dipole
change.
The open directions are unwrapped around a weighted circular ionic center, so
a wire that straddles a supercell boundary is integrated as one contiguous
object rather than being cut at the cell edge.

The supercell dielectric tensor does depend on vacuum. ZStar therefore reports
the intrinsic electronic line polarizability

```text
alpha_1D = A_perp (epsilon_supercell - I) / (4 pi)
```

in `Angstrom^2` in `response.json`. The frequency-dependent `zstar ir`
and `zstar dielectric static` outputs report
`alpha_1D/epsilon_0 = A_perp (epsilon_supercell - I)` in `Angstrom^2`.

## Unified BEC and Gamma-phonon workflow

Prepare the default symmetry-reduced Phonopy ensemble in a fresh work directory.
Keep `KPT` next to the supplied `INPUT` to preserve the example's axial mesh:

```bash
zstar bec pre --stru STRU --input INPUT --dim 1 --symmprec 1e-5

zstar bec job --system shell --dim 1 --output run.sh
bash run.sh

zstar bec stat --root .
zstar bec post --root .
```

The default `--ensemble phonopy` and `--method auto` reuse each SCF's polarization
and forces to reconstruct both BECs and the Gamma Hessian. No additional phonon
SCFs are required for Gamma spectroscopy. `--ensemble cartesian` retains the
legacy BEC-only route; it must not be confused with the unified default.
The executor runs `0.no-move` first, checks the automatic one-dimensional
high-symmetry band path along the periodic axis with PYATB, and stops before
all displacements if the gap is below the selected threshold. Every
displacement reuses the converged reference charge density, and completed
stages are skipped when the driver is restarted.

Important outputs are:

- `BEC.dat`: full symmetry-expanded, charge-neutral BEC tensors;
- `BORN`: supercell electronic dielectric tensor plus primitive BEC tensors;
- `response.json`: calculator-neutral response record with intrinsic
  line polarizability;
- `FORCE_CONSTANTS`, `qpoints.yaml`: Gamma force constants and eigensystem;
- `response_fit.json`: actual displacements, joint observations and fit diagnostics;
- `BEC.raw.dat`, `FORCE_CONSTANTS.raw`: values before constraint projection.

Executable paths and MPI/OMP settings can come from the ZStar configuration.
Scheduler directives and module activation belong in the job header. Selection
is **Specified** (`--header FILE`) > **Current** (`./header.sh`) > **Global**
(`~/.zstar/header.sh`). Without a header, an editable commented template is emitted.

## Gamma phonons, IR, and Raman

For the BN and Sb2S3 examples, use the unified `qpoints.yaml` directly. The supplied
`run.sh` performs rigid-mode checks and the complete IR/Raman sequence. A separate
supercell phonon calculation is needed only when extending to finite wavevector:

```bash
zstar phonon pre --stru STRU --dim "1 1 2" --physical-dim 1
# Run every disp-* ABACUS force calculation.
zstar phonon run --root .
zstar phonon post --root .
zstar phonon irrep --root . --file irreps.yaml --mode db --acoustic-thz 0.5
```

Do not add `--nac` for this Gamma workflow. A bulk 3D non-analytic correction
is not a valid substitute for one-dimensional electrostatics.

A free wire has four acoustic branches at Gamma: one longitudinal, one
torsional, and two flexural branches. The flexural frequencies are especially
sensitive to finite-displacement and force-constant noise and can appear as
small imaginary values. The explicit `0.5 THz` classification threshold above
is suitable for the distributed GaAs benchmark, whose next optical mode is
well separated at about `1.29 THz`; users should review this separation for
their own structures instead of applying the value blindly.

Calculate the Gamma-point IR response:

```bash
zstar ir --qpoints qpoints.yaml --born BEC.dat \
  --dielectric BORN --dim 1 --periodic-axis z --outdir ir_spectrum

zstar dielectric static --qpoints qpoints.yaml --born BEC.dat \
  --dielectric BORN --dim 1 --periodic-axis z --outdir dielectric_response
```

For Raman spectra, first select stable optical modes from `qpoints.yaml`:

```bash
zstar raman prepare --stru STRU --qpoints qpoints.yaml \
  --modes 17,21,24,29,37,39,40,41,55,57 --outdir raman
zstar raman run --raman-dir raman --reference 0.no-move \
  --qpoints qpoints.yaml --dim 1 --periodic-axis z \
  --abacus-command "mpirun -np 20 abacus" \
  --pyatb-command "mpirun -np 20 pyatb"
```

ZStar converts the vacuum-dependent dielectric derivative to the line
polarizability derivative `d alpha_1D / dQ` in
`Angstrom^2/(Angstrom sqrt(amu))` before calculating Raman activities.
The mode list above reproduces the representative GaAs validation subset and
covers all four `mm2` irreducible representations. It is a selected-mode
Raman benchmark, whereas the accompanying IR calculation contracts the BECs
with every stable optical mode.

## Legacy GaAs benchmark (separate calculations)

The distributed 24-atom hydrogen-passivated GaAs nanowire completed 49
reference/BEC stages and 40 phonon-force stages. Its default PYATB band gap along
the periodic direction is `3.3994 eV`. Automatic atom matching against an independent VASP calculation
gives a full-tensor BEC RMS difference of `0.02068 e` and a maximum component
difference of `0.08906 e`. The periodic-axis line polarizabilities are
`27.099 Angstrom^2` from ABACUS + PYATB and `27.218 Angstrom^2` from VASP.

The four near-zero Gamma branches span `-10.00` to `-1.70 cm^-1`. For the 56
stable lattice modes below `800 cm^-1`, comparison with the archived Quantum
ESPRESSO reference gives `MAE = 7.6878 cm^-1` and `RMSE = 8.8459 cm^-1`.
ZStar retained all 68 positive-frequency IR modes and completed the disclosed
ten-mode Raman subset through 20 positive/negative electronic-response stages.
Compact inputs, outputs, hashes, and plotting data are archived under
`docs/paper_figures/source_data/gaas_nanowire`.

Only the periodic `z` electronic line polarizability is used for the
like-for-like VASP comparison. VASP `LEPSILON` includes DFT local-field
effects, whereas the PYATB Kubo response is independent-particle, so the
transverse electronic-response difference is retained as a convention
diagnostic rather than reported as agreement.

## Unpassivated Examples

Three additional ABACUS/PYATB examples are available under
`examples/IR_Raman_Spectra`: `Nanotube_BN_6_0`, `Nanotube_BN_9_0`, and
`Nanowire_Sb2S3`. Both BN tubes use PBE; the Sb2S3 full chain uses PBE-D3(BJ),
not HSE. All are centered in xy and periodic along z, without hydrogen termination.
Each includes `run/`, `run/relaxation/`, `results/`, bilingual READMEs, `run.sh`,
pseudopotentials, orbitals and an optimized `structure.vasp` for visualization.

| Case | Band gap (eV) | Nonrigid Gamma modes | Lowest (cm^-1) | BEC + Gamma core-hours | Raman core-hours |
|---|---:|---:|---:|---:|---:|
| BN(6,0) | 2.799 | 68 | 99.20 | 27.0 | 119.8 |
| BN(9,0) | 3.813 | 104 | 47.92 | 125.0 | 294.3 |
| Sb2S3 | 1.501 | 26 | 39.38 | 18.9 | 30.1 |

Costs sum completed ABACUS and PYATB calls, excluding preparation overhead and
geometry optimization. BN(9,0) also excludes the unrecorded interrupted PYATB
call during a cu20 reboot. Full stage accounting is in `results/compute_costs.json`.
Reference geometry optimization costs are 13.6, 22.4 and 36.1 core-hours,
respectively. These are allocated core-hours, not integrated CPU-utilization time.

The runner rejects incompatible work paths and changed input hashes, reuses
completed stages, checks reference forces and insulation, and excludes three
translations plus axial rigid rotation using mass-weighted eigenvector overlaps.
All other modes are calculated, including weak/inactive modes; no peak shifts or
intensity fitting are applied. This proves neither finite-q stability nor absolute
Raman-intensity accuracy.

For BN(6,0), seven candidate IR branches differ by at most 3.1% from the explicit
CRYSTAL/B3LYP values in Erba et al., Table I
([DOI](https://doi.org/10.1063/1.4788831)); the breathing mode is 408.45 versus
414.41 cm^-1 and has radial overlap 0.99684. Branch assignment uses frequency
order, multiplicity and polarization, not unavailable reference eigenvectors.
BN(9,0) Raman is compared qualitatively with Wirtz et al.
([DOI](https://doi.org/10.1103/PhysRevB.71.241402)); low-frequency relative
intensities differ, and transverse depolarization/local fields cannot be assumed
equivalent to the independent-particle PYATB response.

For Sb2S3, the original sampled IR/Raman curves in the public
[CRYSTAL/B3LYP-D3(BJ) dataset](https://doi.org/10.17632/6tntvw37tr.1) are retained
without frequency shifts in the comparison figure. Raman relative intensities
differ substantially. Its 31.5762 cm^-1 reference mode has approximately 98.3%
axial-rotation overlap from printed eigenvectors; this feature is disclosed, not
silently removed from the reference curve. Different XC and response approximations
preclude interpreting the comparison as a same-method quantitative benchmark.

## BEC presentation and efficiency accounting

For BN(9,0), rotate each tensor into its atom-local radial/tangential/axial frame
before averaging over a species. The B means `(Zrr, Ztt, Zzz)` are
`(0.397, 1.256, 2.745) e`; N means are `(-0.474, -1.178, -2.745) e`.
Do not apply a componentwise neutrality test to sums expressed in different local
frames. All-atom Cartesian tensors, local ranges, and source hashes are in
`Nanotube_BN_9_0/results/BEC_comparison/`.

For Sb2S3, the representative atoms `(7,8,1,2,3)` have axial charges
`(4.642, 5.972, -4.101, -3.353, -3.159) e`. After mapping the reference atom order
and rotating its periodic x axis to z, the public B3LYP-D3(BJ) data give
`(4.341, 6.135, -3.786, -3.430, -3.260) e`. The full three-diagonal comparison
and matching diagnostics are in `Nanowire_Sb2S3/results/BEC_comparison/`.
The reference is [Ulian's computational dataset](https://doi.org/10.17632/6tntvw37tr.1),
not a verified associated journal article. Independent relaxed geometries and XC
methods make this a tensor-pattern comparison, not a matched-method accuracy test.

| Case | Separate BEC SCFs | Separate phonon SCFs | Separate total | Unified joint SCFs |
|---|---:|---:|---:|---:|
| BN(9,0) | 61 | 56 | 117 | 57 |
| Sb2S3 | 31 | 20 | 51 | 21 |

| Case | Separate BEC core-h | Separate phonon core-h | Separate total core-h | Unified joint core-h | Speedup |
|---|---:|---:|---:|---:|---:|
| BN(9,0) | 140.05 | 130.36 | 270.41 | 125.04 | 2.16 |
| Sb2S3 | 23.74 | 17.93 | 41.67 | 18.95 | 2.20 |

Counts include one reference in the BEC route and none in the additional
force-only route. Unified shares every reference/displacement SCF between both
observables: its BEC and phonon costs cannot be added twice. Counts are SCF
calculations, not electronic iterations. For Sb2S3, the matched Separate BEC and
phonon runs cost 23.74 and 17.93 core-hours (41.67 total), versus 18.95 for Unified:
2.20-fold measured speedup, or 54.5% saved. BN(9,0) saves 53.8% of successful
solver core-hours. One interrupted force attempt on cu20 has no complete timing
record; its partial log is retained, and the remaining stages completed on cu25.
Listed costs exclude that interruption and are not total billed usage. No task-count
ratio is reported as measured speedup.
Raman derivatives and optimization are excluded from this benchmark.

For Sb2S3, the raw BEC maximum difference is 0.00104 e and the internal-mode
frequency maximum difference is 0.0184 cm^-1. The all-mode maximum of 0.769 cm^-1
belongs to near-zero axial rigid rotation, classified from eigenvectors in both
routes. The raw Hessian relative difference is 4.91e-5. Native evidence and timing
ledgers are in `Nanowire_Sb2S3/results/benchmark/`.

For BN(9,0), these differences are 0.000208 e, 0.514 cm^-1 (the lowest internal
pair near 48 cm^-1), and 1.18e-5, respectively. Its independently reconstructed
internal modes remain positive. Its benchmark archive uses the same folder layout.
BN9 BEC displacements decrease only from 60 to 56 because the vacuum-cell
symmetry is a subgroup of the full rod group; avoiding 56 duplicate force SCFs
provides the larger saving. The workflow does not claim the minimum possible
displacement count under full rod symmetry.

Recreate the source-backed summaries and comparison figure from the repository root:

```bash
python tools/shared_response/export_one_dimensional_bec.py
python tools/shared_response/plot_sb2s3_comparison.py examples/IR_Raman_Spectra/Nanowire_Sb2S3 --packaged --with-structure
python -m tools.shared_response.verify_one_dimensional_example --case examples/IR_Raman_Spectra/Nanowire_Sb2S3 --verify-archive
python -m tools.shared_response.verify_one_dimensional_example --case examples/IR_Raman_Spectra/Nanotube_BN_9_0 --verify-archive
```

The last two commands need the repository's Python dependencies, but no DFT or
PYATB executable. They reconstruct tensors, recalculate both spectra and verify
native evidence hashes without modifying the case. Where a completed benchmark
is included, its timing ledgers are checked as well. This is a reproducibility
check, not an independent validation of the electronic response approximation.

### Dimension-indexed BEC cases

The dimension-indexed BEC/Gamma bundles are now `examples/1D_Nanowire/BN_9_0`
and `examples/1D_Nanowire/Sb2S3`. Their `run/`, `results/`, and `run.sh` do not
duplicate the full spectroscopy workflow. Verify either response-only bundle with:

```bash
python -m tools.shared_response.verify_one_dimensional_example \
  --case examples/1D_Nanowire/BN_9_0 --verify-archive --response-only
```

Omitting `--response-only` still requires complete IR/Raman outputs; the verifier
does not silently accept missing spectra.

### Finite-wavevector electrostatics

Gamma-point mode-resolved IR and Raman spectra are well-defined and supported.
At finite wavevector, polar one-dimensional phonons have a different
long-range electrostatic kernel from both bulk and slab systems. ZStar rejects
bulk/Gonze NAC for `dim=1`; dispersion calculations that include the polar
long-range term require a calculator with a genuine 1D Coulomb cutoff. See
[Rivano, Marzari, and Sohier (2023)](https://doi.org/10.1038/s41524-023-01140-2)
and [Rivano, Marzari, and Sohier (2024)](https://doi.org/10.1103/PhysRevB.109.245426).
