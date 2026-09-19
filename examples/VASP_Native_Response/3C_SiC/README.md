# VASP native response: 3C-SiC

This bulk PBE case starts with cell relaxation and validates native electric
DFPT, Gamma phonon DFPT, native strain finite differences, and mixed-route Raman.
It is not a literature accuracy benchmark until its convergence and references
are recorded in `results/`.

`run/` contains clean inputs. `results/` contains validated compact outputs
only after the calculation has completed. Large outputs remain in `.work/`.
VASP and its licensed POTCAR files are not included in the repository.

Install `zstar[vasp]`, load VASP, and set `VASP_PSEUDO_ROOT`. POTCAR is assembled
in POSCAR order from `$VASP_PSEUDO_ROOT/PBE/Si/POTCAR` and `PBE/C/POTCAR`.
On hf, submit `sbatch run_hf.slurm`: 64 MPI ranks, 1 OpenMP thread, no fixed
node, and no exclusive allocation. `run.sh` retains completed stages on restart.
`MPI_TASKS` and `VASP_COMMAND` override the rank count and launcher.

To follow the response steps manually after relaxation:

```bash
zstar bec pre --calculator vasp --input-dir .work/input --root .work/dfpt --phonons
zstar bec run --root .work/dfpt --vasp-command 'mpirun -np 64 vasp_std'
zstar bec post --root .work/dfpt
zstar spectra pre --calculator vasp --response .work/dfpt --root .work/raman
zstar spectra run --root .work/raman --command 'mpirun -np 64 vasp_std'
zstar spectra post --root .work/raman
```

The separate `--elastic` validation route uses native `IBRION=6, ISIF=3`
because strain perturbations are not implemented in VASP phonon DFPT.
It supplies a complete elastic matrix for conversion from `e` to `d`.
The collector reports internal-strain force-balance warnings and rejects
derived d when the native quality checks fail; normal termination alone
does not validate all electromechanical tensors.
DFPT and native finite-difference optical frequencies can then be compared
at identical geometry, functional, potentials and integration settings.
