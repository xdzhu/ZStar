# Quantum ESPRESSO response examples

These CO₂ and zincblende SiC inputs completed the ZStar `pw.x`, `ph.x`, and
`dynmat.x` workflow with Quantum ESPRESSO 6.2.1. Both cases use PBE and
calculate Γ-point dielectric tensors, effective charges, and infrared
activities. The archived runs used no Raman calculation.

| Case | Purpose | SCF gap |
| --- | --- | ---: |
| [CO₂](CO2/) | Isolated-molecule interface check on an unrelaxed structure | 8.5182 eV |
| [SiC](SiC/) | Bulk response and mode-parsing check | 1.3553 eV |

The SiC optical triplet is at 785.39 cm⁻¹. Its archived Born charges sum to
−0.1833 e per Cartesian direction before the acoustic sum rule is imposed.
The inputs illustrate execution and parsing. For a materials benchmark,
converge the basis cutoff and k-point mesh for the property of interest.

## Run an example

From this directory, set `case=CO2` and `dim=0` for the molecule, or set
`case=SiC` and `dim=3` for the crystal. Put the UPF files named in
`$case/run/pw.in` in `$case/run/pseudo/`. The input names and archived
`pw.out` identify the required pseudopotentials. Use QE executables on
`PATH` or pass the commands for your installation.

```bash
case=CO2
dim=0
work="qe_work_$case"
zstar bec pre --calculator qe --input "$case/run/pw.in" --root "$work" --dim "$dim" --no-raman
zstar bec run --root "$work"
zstar bec stat --root "$work"
zstar bec post --root "$work"
```

Each `results/` directory contains the native solver outputs, the stage
summary with archive hashes, and the resulting ZStar response record.
The SCF inputs reproduce the archived settings with a relative path for
pseudopotentials. See the [backend guide](../../../docs/calculator_independent_backends.md#quantum-espresso)
for MPI and scheduler examples.
