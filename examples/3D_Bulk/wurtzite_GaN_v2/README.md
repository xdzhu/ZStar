# wurtzite GaN v2 piezoelectric gate

This is the first calculator-level v2 piezoelectric validation case. It is a
research case, not a stable CLI example, until the Gate C conditions in
[`docs/v2_piezo_benchmark_gate.md`](../../../docs/v2_piezo_benchmark_gate.md)
are met.

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

The directory intentionally does not contain pseudopotentials or orbitals.
On the shared validation nodes use the Dojo Ga/N assets recorded in
`provenance.json` and copy them into each private run stage. Do not commit
large calculator outputs to this source directory.
