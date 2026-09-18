# Wurtzite AlN: Native VASP Response

This four-atom PBE example starts with cell/internal-coordinate relaxation,
then computes BEC, electronic and phonon dielectric tensors, Gamma phonons,
piezoelectric and elastic tensors, IR and mode-derivative Raman spectra.
Cartesian z is parallel to +c; the axial Al-to-N bond points along +c.
The starting geometry is a seed, not a claimed equilibrium structure.

## Run

Install ZStar with its VASP spectroscopy dependencies and load VASP.
Set `VASP_PSEUDO_ROOT` to your licensed pseudopotential library. The script
assembles PBE/Al and PBE/N POTCAR files in POSCAR species order.

```bash
bash run.sh
```

On the configured hf cluster, `sbatch run_hf.slurm` requests 64 MPI ranks,
one OpenMP thread each, no exclusive allocation and no fixed node. Native
inputs use `NCORE = 4` without NPAR. Change the Slurm header and launcher
for another machine. `ISYM = 0` keeps the k-point set unchanged through
native perturbations in the tested VASP build; this does not retain
electronic symmetry reduction.
`MPI_TASKS` and `VASP_COMMAND` can override the runner's rank count and launcher.

The stages are resumable. Unconverged relaxation or rejected response stops
the workflow. `run/` contains clean input; `.work/` contains execution files;
`results/` receives compact derived tensors and spectra. To change numerical
settings, use a new execution directory rather than reuse completed stages.

## Verification

Two native ionic routes are compared on the same relaxed structure:
DFPT (`IBRION = 8`) and native strain finite differences (`IBRION = 6`,
`ISIF = 3`). Electronic BEC/dielectric response uses LEPSILON in both.
The latter supplies elastic constants and a derived d tensor if stability,
matrix symmetry and internal-strain force balance pass. Raman uses additional
native dielectric calculations on mode-displaced structures, not Raman DFPT.

`verify_results.py` checks raw OUTCAR BEC, an independent XML dielectric
parser, charge neutrality, optical-mode stability, harmonic dielectric closure,
the 6mm piezo tensor pattern, route frequency agreement and `e = d C`.
It reports native DFPT internal-strain warnings without projecting them away.
These are consistency checks, not a substitute for convergence testing.

`verify_spectra.py` checks the equilibrium 6mm point group, all nine optical
mode IDs, frequency/tensor alignment and IR/Raman selection rules. The outputs
are Gamma TO spectra without directional NAC, not polarization-resolved LO
branches or an absolute experimental-intensity benchmark. Dielectric tensors
include internal ionic relaxation at fixed macroscopic strain, not a free-stress
piezoelectric correction.

The accepted native strain calculation gives e31=-0.582, e33=1.462 C/m2,
and d33=5.324 pm/V. Historical relaxation/DFPT used EDIFF=1e-8; the accepted
elastic route and Raman use 1e-9. The supplied clean inputs use 1e-9 throughout.
`results/stage_input_sha256.txt` identifies the actual stage inputs; seed hashes
alone do not describe a resumed calculation.

After relaxation, the main steps can be run individually:

For `e` only, prepare `--root .work/piezo --piezo` instead of the elastic
root below. This selects native DFPT ionic response without elastic strain
jobs. The complete `run.sh` compares both routes for validation; routine
piezoelectric calculations do not require that comparison. For `d`, keep
`--elastic` to obtain the complete native elastic matrix.

```bash
zstar bec pre --calculator vasp --input-dir .work/input --root .work/elastic --elastic
zstar bec run --root .work/elastic --vasp-command 'mpirun -np 64 vasp_std'
zstar bec post --root .work/elastic
zstar spectra pre --calculator vasp --response .work/elastic --root .work/raman
zstar spectra run --root .work/raman --command 'mpirun -np 64 vasp_std'
zstar spectra post --root .work/raman
```

For IR only, add `--kind ir`; no additional VASP job is required. Raman tensor
JSON and `qpoints.yaml` use matching ascending-frequency Gamma IDs. Preserve
their pairing when transferring data to other post-processing commands.

## Literature

- de Jong et al., *Scientific Data* **2**, 150053 (2015),
  [DOI:10.1038/sdata.2015.53](https://doi.org/10.1038/sdata.2015.53),
  [author-hosted full text](https://perssongroup.lbl.gov/papers/sdata2015-piezoprops.pdf).
  The technical-validation section gives VASP PBE PAW proper piezoelectric
  coefficients e33 = 1.46 C/m2 and e31 = -0.58 C/m2. Their ENCUT is 1000 eV
  and approximately 2000 k points per reciprocal atom; our initial mesh/cutoff
  are not identical, so deviations must be reported rather than hidden.
- Bernardini, Fiorentini and Vanderbilt, *Phys. Rev. B* **56**, R10024 (1997),
  [DOI:10.1103/PhysRevB.56.R10024](https://doi.org/10.1103/PhysRevB.56.R10024),
  [author-hosted full text](https://www.physics.rutgers.edu/~dhv/pubs/local_copy/fb_nit.pdf).
  Table II reports LDA ultrasoft results: N axial BEC -2.70 e,
  e33 = 1.46 C/m2 and e31 = -0.60 C/m2. These are context rather than
  numerical acceptance thresholds for this PBE PAW calculation; distinguish
  historical polarization-derivative and proper piezoelectric conventions.
- Zoroddu et al., *Phys. Rev. B* **64**, 045208 (2001),
  [DOI:10.1103/PhysRevB.64.045208](https://doi.org/10.1103/PhysRevB.64.045208).
  This work examines LDA/GGA sensitivity; extract tabulated values and
  their conventions before making quantitative comparisons.
