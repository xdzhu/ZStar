# Annotated revision execution, 2026-09-06

Source checklist: `D:/Work/Zstar/zstar-article/annotated/review_20260906_tasks.md`.
Scope: the eleven verified annotations and their necessary dependencies only.
Figure 1 remains author-owned. No release or PyPI upload is implied.

## Progress

- [x] Confirm all eleven annotations and freeze their interpretation (A01-A11).
- [x] Implement canonical `BEC.*` outputs with read-only legacy aliases.
- [x] Full source/tool regression: 410 tests and 66 subtests on Python 3.10.
- [x] Automatic-discovery collision tests and downstream/example migration (A04).
- [x] Validate and calculate the fixed-ion nonpolar GeS reference (A09).
- [x] Audit eight reference-state structures, native band gaps and displacement counts (A05).
- [x] Refresh examples, bilingual instructions, and reproducibility evidence.
- [x] Revise notation, section order, rounded display, and appendices (A01-A03, A06-A08, A10-A11).
- [x] Insert approved BEC/spectroscopy artwork; regenerate six-panel potential figure.
- [x] Audit citations and derive figure reference labels from final bibliography keys.
- [x] Full regression, clean/revision compilation, page-by-page visual checks and frozen delivery inputs.

## Evidence and constraints

GeS polar source: `235:/home/zhuxd/abacus/agent-runs/20260903-zstar-ges-potential`.
Confirmed settings: ABACUS 3.10.0 LTS, PBE, DOJO NC, DZP 10-au orbitals,
100 Ry, kspacing 0.05 0.05 1, SCF 1e-8, Gaussian 0.001 Ry, D3 zero damping.
The original calculation used 40 MPI ranks and one OMP thread.
cu23 was idle at inspection. Only cu23-cu26 are authorized for this revision.

Primary reference inspected: Fei, Kang and Yang, Phys. Rev. Lett. 117, 097601
(2016), DOI 10.1103/PhysRevLett.117.097601, accepted manuscript pp. 1-2,
Fig. 1 and its discussion. Zero tilting produces an inversion-symmetric
nonpolar reference. Our fixed-cell projection must be checked independently;
it is not evidence of a saddle point or a minimum-energy switching path.

Historical calculation archives and source logs remain unchanged. Canonical
copies must retain provenance; precision and tensor conventions are unchanged.

## Completed GeS control

The fixed-ion calculation completed on cu23 with 40 MPI ranks, one OMP
thread, and 39 solver seconds (0.4333 core-h). The SCF log confirms density
convergence. Equal-species inversion pairs have zero fractional residual;
spglib identifies the reference as Pmmn (59), versus Pmn2_1 (31) for the
polar source. The reference is not presented as a verified saddle point.

`examples/Electrostatic_Potential/GeS_nonpolar/` now contains clean inputs,
PP/ORB assets, a native compressed cube, native SCF log, construction and
checksum evidence, bilingual instructions, and a runner supporting either
offline regeneration or an explicit fresh SCF. The offline runner passed,
including verification that the private input cube did not change.

The common-scale six-panel potential figure was regenerated from its
original Python source and visually inspected. Maps are tiled 3x3 only for
plotting. Mirror residuals: polar GeS 0.0983; nonpolar reference 2.36e-8.

The manuscript's 1D BEC section was moved before molecular APTs; the
approved 1D structure PDF and latest four-row spectroscopy PDF were copied
to TeX-level Figure_ filenames. The redundant standalone Sb2S3 figure was
removed. Citation numbers are now generated from the compiled bibliography:
HfO2 41, MoS2 54, Sb2S3 45 and CH4 53. The 291 drawing paths, four original
lossless structure images and placements are unchanged by label synchronization.

## Case and source checks

- `reference_state_table_20260906.json` records all eight structure hashes,
  actual displacement counts, native band-gap evidence and the distinction
  between prepared inputs and measured timing. In2Se3 PBEsol is not mixed with
  the PBE efficiency archive.
- HfO2 bulk and spectroscopy inputs now match the manuscript's PBEsol, 9-au,
  100-Ry, 10x10x7, SCF 1e-8 reference. Earlier inputs/results remain separately
  under `legacy/before_20260906/`, never overwritten with different provenance.
- Generic example launchers respect ZStar configuration and environment
  overrides. Molecule IR is collected from mode dipole derivatives. Linux
  solver-free execution tests passed on cu23, including distinct-case aliases.
- BN(9,0): 2269 native and 624 benchmark files verified; 270.413924/125.035243
  core-h gives 2.162702 speedup. Sb2S3: 685 native and 282 benchmark files;
  41.669086/18.945064 gives 2.199469. Offline tensors and spectra reproduce.
- 130 canonical result copies retain original numerical bytes. Historical
  logs and compressed archives remain immutable; see the migration manifest.

## Manuscript and citation checks

The clean and blue-revision builds use the same source, 56 DOI-linked
references and all nine Figure_ PDF basenames. The source-specific citation
audit distinguishes metadata verification, retained full-text numerical
evidence, and current HTTP/SSL access restrictions; it does not claim 56 new
full-text downloads. The redundant DOI-free Kittel citation was removed, not
assigned a spurious search-result DOI. Literature frequency-only envelopes
and Sb2S3 Raman intensity disagreement remain explicit.

The full-resolution spectroscopy layout preserves the author's edits.
The potential figure now occupies the relevant results pages without the
previous avoidable blank page. Input listings remain intact, with aligned
parameter/value columns. Figure 1 is intentionally unchanged and remains
the author's final artwork task; no final journal submission is claimed.

## Frozen delivery inputs

Version 0.3.0rc4 builds as a pure-Python `py3-none-any.whl` and an sdist;
both pass `twine check` and exclude examples. A separately installed wheel
passes the same 410 tests and 66 subtests. The full delivery retains examples,
PP/ORB assets and evidence outside the wheel. The packager verifies each ZIP
member against SHA256 and rejects symlinks and internal NbSe2 paths.

Final clean/revision PDFs each contain 35 pages and have identical extracted
text. All figure references and 56 bibliography numbers are stable. No
undefined references, content overflow, or split input listings remain;
the standard first-page footer has a harmless 1.9-pt horizontal-box warning.
The source-only manuscript archive has all nine Figure_ PDFs beside the TeX.
English/Chinese manuals contain 22/19 pages and the updated four-row figure.
