# 3C-SiC: Unified BEC and Gamma phonons

Two-atom primitive cell; PBE, SG15 ONCV pseudopotentials, DZP 7-au orbitals,
100-Ry cutoff, Gamma-centered 13x13x13 mesh, SCF threshold 1e-8.

Run `bash run.sh` after configuring ABACUS/PYATB. Add `--with-spectra` to
continue from the Unified BEC/Gamma calculation to IR and Raman:

```bash
bash run.sh --with-spectra --dry-run
bash run.sh --with-spectra
```

Inputs and basis files are in `run/`; retained outputs are in `results/`; a
new calculation uses `work/`. The main BEC and Gamma files are written directly
under `work/`, while plots and tables are written under `work/spectra/ir/` and
`work/spectra/raman/`. The corresponding retained spectra are available under
`results/spectra/` in tabulated, PNG, PDF, and SVG formats.
The shared automatic-sign set has two physical displacements; the matched
Cartesian central set has twelve. Both also calculate `0.no-move`.

Compare full raw/projected Born tensors, the Gamma Hessian and optical triplet,
and the stable phonon dielectric response. See the parent README and benchmark
JSON for exact results and measured costs. This is an internal numerical
equivalence test, not an accuracy claim against experiment.

The Unified result gives opposite Si/C diagonal BEC values of 2.70094 e and
three degenerate IR- and Raman-active optical modes at 772.645 cm^-1.
