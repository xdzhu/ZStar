# wurtzite GaN v2 piezoelectric gate

This is the first calculator-level v2 piezoelectric validation case. It remains a
research case, not a stable CLI example; the completed result is conditional as
documented in
[`docs/v2_piezo_benchmark_gate.md`](../../../docs/v2_piezo_benchmark_gate.md).

The four-atom hexagonal Bravais primitive cell is oriented with `z || [0001]` and uses the
`6mm` symmetry of wurtzite GaN. The planned response ensemble contains one
reference plus `+/-` perturbations for all six engineering-Voigt strain
components. Each completed geometry is post-processed by one PYATB run, which
returns all three `a/b/c` polarization directions. No three-direction ABACUS
NSCF duplication is used.

The input lattice and internal coordinate are the literature starting point
(`a=6.040 bohr`, `c/a=1.6336`, `u=0.376`) from Bernardini, Fiorentini and
Vanderbilt, PRB 56 R10024 (1997). The `STRU` vectors are the equivalent
Angstrom values because this repository uses `LATTICE_CONSTANT=1.889726`.
They are not silently treated as a relaxed
PBEsol equilibrium: the reference force/stress audit must pass before a
material constant is reported.

The completed first-pass result is in `results/piezo_fit.json`; the three-amplitude
and clamped-ion audit is in `results/amplitude_audit.json` and
[`docs/v2_abacus_gan_amplitude_audit_20260913.md`](../../../docs/v2_abacus_gan_amplitude_audit_20260913.md).
The current recommended research step is `+/-0.001` engineering strain. The
`+/-0.0005` set is a numerical-noise audit and `+/-0.002` is a nonlinearity audit.

Only the proper `e` tensor and the mechanically derived `d` values are recorded
for this case. `g`, `h`, `C^D`, and `epsilon^T` are intentionally not reported:
the case does not yet contain an explicitly annotated `epsilon^S` tensor under
the required thermodynamic boundary. Once such a dielectric result is added,
`zstar.v2.derive_electromechanical_forms` can produce those reciprocal forms
without changing the first-principles data.

The directory intentionally does not contain pseudopotentials or orbitals.
On the shared validation nodes use the Dojo Ga/N assets recorded in
`provenance.json` and copy them into each private run stage. Do not commit
large calculator outputs to this source directory.

This is a historical `±0.1%` research result, not the frozen production result.
Its qualification status and separate `d33` comparison are in
[the v2 piezoelectric case matrix](../../../docs/v2_piezoelectric_case_matrix.md).
