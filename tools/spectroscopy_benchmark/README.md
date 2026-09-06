# Bounded Unified spectroscopy benchmark

The tested reconstruction is now in `zstar.raman_response` and the canonical
`zstar spectra` lifecycle. This directory retains bounded benchmark drivers,
not a second implementation of the response kernel.
Four representatives: tetragonal HfO2 (3D), monolayer MoS2 (2D), Sb2S3 (1D),
and CH4 (0D). Existing BEC/force calculations are reused without rewriting them.

1. Audit settings, structures, completed matrices, and existing Raman evidence.
2. Test the rank-three reconstruction against exactly covariant synthetic tensors.
3. On cu23--cu26, calculate only missing static electronic responses in private
   copies of matrix files. This Unified route runs no ABACUS and links no cubes.
4. Reconstruct G[k,a,b,c] = d epsilon[a,b] / d u[k,c] from symmetry-generated
   displacement orbits; rotate all three Cartesian indices, not only two.
5. Contract with mass-weighted Gamma eigenvectors and apply the same dimensional
   normalization as the existing Raman code. Retain raw residuals.
6. Compare with Cartesian central-response reconstruction and existing direct
   mode-displacement Raman results where settings/geometry allow comparison.
7. Account separately for measured BEC/force, added optical responses, and legacy
   mode-displacement Raman. Distinguish assembled costs from a fresh timed
   end-to-end workflow. No inferred cost is labeled measured.

IR needs no new electronic-response kernel after the BEC/force fit. For Raman,
the relation is d epsilon / d q[m] = sum[k,c] G[k,:,:,c] e[m,k,c]/sqrt(M[k]).
The tensor transforms with three rotation matrices. Completeness requires a
rank-three displacement orbit for each inequivalent atom. This algebra does
not guarantee finite-step or Brillouin-zone convergence; the numerical
comparison is an acceptance gate, not an assumed outcome.

The existing 1D conventional Raman costs are reusable. The MoS2 publication
uses a 3x3x1 phonon supercell, whereas its current paired efficiency controls
are primitive-cell Gamma calculations. Those are not interchangeable timing
baselines. Molecular benchmarks use the reoptimized geometry rather than the
older quick-start geometry. Keep these distinctions in the report.

Matched conventional mode-Raman controls are complete for HfO2, MoS2 and reoptimized
CH4. They add 30, 12 and 18 SCFs, respectively; they reuse the existing
reference density by copying, and reuse the existing force modes and settings.
No relaxation, BEC, or phonon SCF is repeated. The positive reference band gap
is verified read-only before running. Optical blocks match the atomic ensemble.

Status: all four atomic-response jobs and direct-mode Raman validations are
complete. The public CLI has passed a real CH4 run and no-solver resume on cu26;
all four packaged `run.sh --post-only` checks pass. Code, manuals and manuscript
now describe the same Unified response route.

Results: `docs/research/unified_spectroscopy_20260906/`. Rebuild from the archived
static outputs (no DFT or PYATB execution needed):

```bash
python -m tools.spectroscopy_benchmark.merge_controls \
  docs/research/unified_spectroscopy_20260906/evidence/HfO2/direct_control
# First run collect and validate_direct for each of HfO2/MoS2/Sb2S3/CH4.
python -m tools.spectroscopy_benchmark.report \
  --root docs/research/unified_spectroscopy_20260906/evidence \
  --out docs/research/unified_spectroscopy_20260906
python -m pytest tools/spectroscopy_benchmark/test_atomic_raman.py \
  tests/test_spectra.py tests/test_shared_response.py -q
```

`collect.py` reconstructs the atomic tensors from each archived static-output
ensemble; `validate_direct.py` compares them with retained mode derivatives.
The report command uses their already archived products. Run these modules with
`--help` to repeat the full local reconstruction. Remote scripts are intentionally
bound to the audited campaign sources and authorized nodes; they are not a new CLI.

Figure contract: Python quantitative grid, four dimension representatives and
two columns (IR/Raman). Show agreement on a common amplitude scale, not separately
rescaled curves. IR uses each ensemble's own phonons; Raman uses the direct-mode
eigenbasis to isolate dielectric-derivative reconstruction. Absolute tensor and
activity L2 errors are reported separately. Export editable SVG, vector PDF,
high-resolution PNG and numerical NPZ/JSON. These are research review figures,
not replacements for existing manuscript figures. All four spines, inward ticks,
plain parenthesized panel letters, and no arbitrary peak shifts.

## What is being tested

At fixed cell and zero wave vector, let
`G[k,a,b,c] = d(epsilon_infinity[a,b])/d(u[k,c])`.
An existing atomic displacement observes `delta_epsilon[a,b] = G[k,a,b,c] u[c]`
to first order. For a symmetry operation with Cartesian rotation `R` and atom
permutation `p`, the corresponding observation is `R delta_epsilon R.T`
at atom `p[k]` with displacement `R u`. Thus the response has three rotating
indices, whereas an ordinary dielectric tensor has two. Each site's expanded
displacement orbit must span three directions. Equivalent-atom mapping then
reconstructs the complete derivative field.

The same mass-normalized eigenvectors used for the IR mode charges give
`d(epsilon[a,b])/dq[m] = sum[k,c] G[k,a,b,c] e[m,k,c]/sqrt(M[k])`.
The code retains the source convention: bulk dielectric derivative; slab
height times dielectric derivative; Gaussian molecular/wire polarizability
derivatives with volume/(4*pi) or cross-section/(4*pi). No field-convention
conversion or arbitrary intensity rescaling is introduced by the reconstruction.

This is a linear-response chain rule and a reduction of repeated electronic
calculations, not a new Raman-scattering theory. It covers the existing static,
nonresonant Placzek model. It does not claim resonant Raman or replace supercell
force calculations needed for phonon dispersion. Symmetry is imposed in the fit;
the translational sum-rule residual is reported without an additional projection.

Method context: ASE's official [Raman documentation](https://docs.ase-lib.org/ase/vibrations/raman.html#placzek)
already describes polarizability-derivative Raman analysis in the Placzek
approximation. The benchmark's contribution is reuse and symmetry reconstruction
within the ZStar displacement workflow, not priority for the derivative formula.

The direct-control optical grids and numerical kernels are held fixed. Comparisons
use the direct mode eigenvectors, which removes arbitrary phase/degenerate-basis
differences. The IR overlays separately compare each route's own mode frequencies.
