# ZStar v2 piezoelectric benchmark index

This is the case-facing index for the three-dimensional piezoelectric campaign.
It deliberately distinguishes a fixed-protocol algorithm audit, research evidence,
diagnosed-but-unqualified results, and active calculations. The full numerical
table, standalone `d33` comparison, protocol, units, and literature provenance are
in [the v2 piezoelectric case matrix](../../../docs/v2_piezoelectric_case_matrix.md).

The [VASP primary-literature comparison](../../../docs/v2_vasp_piezo_literature_comparison_20260918.md)
adds functional-matched PTO/AlN targets, a standalone PTO `d33` comparison,
and explicitly labeled PBE GaN references. It does not equate cross-backend
agreement with an identical-Hamiltonian validation.

Do not treat this index as a set of downloadable reference tensors. A result enters
the quantitative benchmark set only after the protocol, rank/residual, symmetry,
mechanical-stability, and matched-theory comparison gates all pass.

## PBE dual-backend campaign (2026-09-18)

The authoritative [full PBE tensor comparison and separate d33 table](../../../docs/v2_pbe_database_comparison_20260918.md)
now include completed AlN/GaN/ZnO/PTO ABACUS and the already accepted AlN/native VASP.
AlN/ABACUS uses central engineering strain ±0.005 and passes the internal
rank, insulating, tensor-symmetry and mechanical-stability checks:
e33=1.387956 C/m², d33=4.975410 pm/V. Its e33 differs by 5.01% from the
same-phase de Jong PBE database. This is not an identical-input comparison.

| Material | ABACUS/PYATB PBE | Native VASP PBE |
|---|---|---|
| AlN | Complete full e/C/d, internally consistent, external differences reported | Reuse accepted full e/C/d; ENCUT600 rather than database1000 eV disclosed |
| GaN | Complete full e/C/d; d33=1.872239 pm/V, internal checks pass; database e15 difference35.07% retained, not strict external reproduction | Original and single symmetry-control e/C collected; force balance improves but d gate remains pending |
| ZnO | Complete direct e/C/d; d33=9.666372 pm/V, database e Frobenius difference1.73%; auxiliary Lambda symmetry gate remains pending | e/C collected; same warning, d not accepted; explicit frame transformation documented |
| PTO | Complete full central e/C/d; d33=49.084674 pm/V; internal checks pass, PBE database e33 difference24.26% retained, not strict external reproduction | Complete e/C collected and compared with PBE database; internal-strain warning retained, native d gate pending |
| Ordered PZT50/50 [001] | Last audited 7/12 strain points complete, including newly checked strain003−; original cu25/cu26 calculations continue. PBS714459 strain005− failed after100 steps; isolated HF27722565 CG reset relaxation converged, but polarization/build compatibility remain unchecked and it is not an accepted original ensemble point | Original native e/C complete (72/72); exact-symmetry ISYM1 control also complete (48 perturbations), native d still rejected; no matching ordered-model database entry |

Near agreement of a single e component does not override a failed quality gate.
The database provides e only; missing database C/d33 are not manufactured.
Qualified AlN/GaN/ZnO d33 comparators can be derived from the separate frozen
elastic archive; they are not database-reported d or same-calculation pairs.
See [the cross-archive reference audit](../../../docs/v2_pbe_cross_archive_d_reference_20260919.md)
for full C comparisons, geometry/domain differences and signed d33 differences.
Original native tensors, warnings, axis/domain audits and complete 18-component
comparison CSVs are retained in the research result directory cited by the report.
Diagnostic acoustic projection is never substituted for accepted native results.
Actual native perturbations in the completed GaN/PTO archives use engineering
strain ±1% and atomic displacement ±0.01 Å; ABACUS uses central strain ±0.5%.
These are functional-matched comparisons, not identical perturbation protocols.
PZT ISYM=1 initially changed only the native hardcoded ISYM=0. Symmetry worked,
but internal k-point switching failed with NCORE=4. A new ISYM=0/1 pair uses
common NCORE=1, unchanged geometry/precision, 32 MPI x 1 OMP. Both full-response
arms subsequently failed: ISYM0 with scheduler-confirmed OOM and ISYM1 with a
G-vector-count mismatch during a k-point-star transform. A separately tracked
exact-symmetry fixed-ion DFPT diagnostic tests the latter hypothesis; it is not
an accepted full-response result. See the
[control record](../../../docs/v2_pzt_vasp_isym_control_20260918.md);
reference-only timing benefits are separate from the still-pending full-response
speedup and tensor-consistency comparison.

The separately tracked [ordered PZT model results](../../../docs/v2_pzt_ordered_model_results_20260919.md)
retain full tensors and actual60 atomic +12 strain perturbations. The collected
native e33 is2.99118 C/m²; native C is positive definite, but soft elastic directions
amplify d-route sensitivity. Neither diagnostic d33 is promoted to a benchmark
or compared against unmatched ceramic/MPB experimental values.

The later exact-symmetry ISYM=1 control is now completed (HF27722088, 0:0):
actual 36 atomic +12 strain perturbations, full orbit-expanded input ranks30/30 and6/6.
Full native e/C differ from the original by0.384%/0.216% in Frobenius norm.
Native d remains rejected; diagnostic d33 is232.397/250.679 pm/V for the two Xi routes.
The response-OUTCAR time is19.464% lower, but geometry, NCORE and node differ;
this is not an isolated ISYM speedup. Historical pending statements above are superseded
by the [completed control report](../../../docs/v2_pzt_isym_completed_comparison_20260919.md).
ABACUS/PYATB ordered-PZT response is still running; no ceramic comparison is claimed.

## Current PBE e and d33 tables

The [case matrix](../../../docs/v2_piezoelectric_case_matrix.md#当前-pbe-案例优先使用本节勿与历史-pbesol-混写)
now presents current same-phase PBE e31/e33/e15, full-e matrix differences and a
separate d33 comparison before historical snapshots. PTO/PBE d33 is49.084674 pm/V;
the historical PBEsol128.75 pm/V belongs to a different calculation and must not
be substituted. Matched PBE external PTO d33 remains unavailable.
GaN/ZnO/PTO VASP d values are explicitly diagnostic, not accepted native output.
The existing `results/benchmark_comparison.json` is a historical 2026-09-17 snapshot,
including superseded acceptance labels; it is not an authoritative current result.
Use the frozen full-tensor sources linked by the current case matrix instead.

## Earlier frozen-protocol campaign snapshot

The table below records the earlier campaign, not the live PBE queue above.

| Case material | Current case-level evidence |
|---|---|
| wurtzite AlN | Historical PBEsol evidence now quarantined for reference-state consistency risk; use the qualified PBE records above, not this historical acceptance label |
| wurtzite GaN | Historical small-strain result is superseded; frozen-protocol R1 launched on cu25 |
| wurtzite ZnO | Direct result retained as a diagnostic; frozen-protocol R1 launched on cu26 |
| tetragonal PbTiO3 | Ferroelectric longitudinal-response target; HF calculation pending |
| explicitly ordered 50/50 PZT | Model-specific ferroelectric target; HF calculation pending |

Diamond Si, 3C-SiC, and zincblende GaAs remain in the internal validation
record for zero-response, shear-Voigt, and coordinate-transform audits. They
are deliberately not presented here as representative piezoelectric material
cases.
