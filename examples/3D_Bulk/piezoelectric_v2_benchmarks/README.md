# ZStar v2 piezoelectric benchmark index

This is the case-facing index for the three-dimensional piezoelectric campaign.
It deliberately distinguishes a fixed-protocol algorithm audit, research evidence,
diagnosed-but-unqualified results, and active calculations. The full numerical
table, standalone `d33` comparison, protocol, units, and literature provenance are
in [the v2 piezoelectric case matrix](../../../docs/v2_piezoelectric_case_matrix.md).

Do not treat this index as a set of downloadable reference tensors. A result enters
the quantitative benchmark set only after the protocol, rank/residual, symmetry,
mechanical-stability, and matched-theory comparison gates all pass.

| Case material | Current case-level evidence |
|---|---|
| wurtzite AlN | Qualified research evidence; frozen-protocol rerun launched on cu24 |
| wurtzite GaN | Historical small-strain result is superseded; frozen-protocol R1 launched on cu25 |
| wurtzite ZnO | Direct result retained as a diagnostic; frozen-protocol R1 launched on cu26 |
| tetragonal PbTiO3 | Ferroelectric longitudinal-response target; HF calculation pending |
| explicitly ordered 50/50 PZT | Model-specific ferroelectric target; HF calculation pending |

Diamond Si, 3C-SiC, and zincblende GaAs remain in the internal validation
record for zero-response, shear-Voigt, and coordinate-transform audits. They
are deliberately not presented here as representative piezoelectric material
cases.
