# ZStar v2 response gates

This reference is for v2 development and case audits. It is not a replacement
for the equations in `docs/v2_theory.md`, `docs/v2_symmetry_reduction.md`, or the
current implementation tests.

## Gate checklist

Before a case is called a research result, verify:

- `ResponseDocument.schema` is `zstar-v2-response` and its version is supported;
- dimensionality and `periodic_axes` agree at both document and quantity level;
- the reference structure is insulating for Berry polarization;
- the space-group dataset uses the single v2 physical tolerance `symprec=1e-3`,
  with species-preserving atom maps and a right-handed Cartesian basis; a
  different physical symmetry threshold is an input error, not a second result;
- every perturbation has a serialized actual strain/displacement and a paired
  sign where a central difference is claimed;
- each geometry has exactly one PYATB run containing the three lattice-direction
  Berry values, with branch shifts and stage-specific lattice provenance;
- fitted quantities report `input_rank`, `allowed_rank`, `fit_rank`, residuals,
  condition number, units, axes, and boundary conditions;
- elastic fits state stress sign and engineering-Voigt shear convention and have
  positive stability eigenvalues when mechanical stability is claimed;
- relaxed-ion Gamma/internal-strain fits use initial force blocks and an explicit
  acoustic gauge; final zero-force blocks are not substitutes;
- independent-backend or DOI/publisher-verified reference evidence is present
  before promotion to a stable benchmark.

## Promotion labels

- **research**: executable and internally tested, but limited in backend, amplitude,
  boundary, or literature evidence;
- **conditional**: a named gate remains open; suitable for an audit report, not a
  stable user-facing command;
- **stable**: theory, schema, failure matrix, reproducibility, and quantitative
  validation gates all pass;
- **experimental**: theory, boundary conditions, or validation plan is incomplete.

Never promote a result because a single material looks plausible. Preserve the
raw observations and the failed-gate explanation alongside any summary tensor.
