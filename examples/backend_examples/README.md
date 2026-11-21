# Calculator backend examples

These examples show how the calculator-independent ZStar analysis connects to
CP2K, Quantum ESPRESSO, and VASP. Each backend uses its own input syntax and
response conventions.

## CP2K

- `cp2k_bec/H2O`: quantitative ZStar central-difference BEC versus CP2K native
  APT, with a component-wise comparison record.
- `cp2k_bec/MgO`: periodic BEC and native `APT_FD` diagnostic, including the
  documented acoustic-sum residual.
- `calculator_spectroscopy/cp2k_h2o`: retained IR and Raman tables and plots.

The H2O BEC commands are in `cp2k_bec/H2O/README.md`. They require a local
CP2K executable and CP2K data directory; neither is bundled.

## Quantum ESPRESSO

- [CO₂ and SiC](qe_bec/) include inputs, completed QE 6.2.1 solver outputs,
  and ZStar dielectric, effective-charge, and mode records.

## VASP

`calculator_spectroscopy/vasp_sic/` documents the required `INCAR`, `POSCAR`,
`KPOINTS`, licensed `POTCAR`, and `vasprun.xml` inputs. The compact outputs in
`calculator_spectroscopy/vasp_sic/` include the response tables and plots.
`POTCAR` must be obtained under the user's license and must not be committed.

Use `zstar backend list --check` and `zstar config check` before launching a
backend workflow.

Each case uses `run/` for inputs and `results/` for archived outputs. For the
CP2K and VASP cases with a `run.sh` launcher, use `bash run.sh --dry-run` to
check the command sequence.
