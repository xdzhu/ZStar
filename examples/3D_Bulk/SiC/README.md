# 3C-SiC: Unified BEC and Gamma phonons

Two-atom primitive cell; PBE, SG15 ONCV pseudopotentials, DZP 7-au orbitals,
100-Ry cutoff, Gamma-centered 13x13x13 mesh, SCF threshold 1e-8.

After [configuring ABACUS and PYATB](../../../docs/cli_reference.md#calculator-configuration),
make a working copy of the supplied inputs:

```bash
cp -r run work
cd work
```

First calculate BEC and Gamma-point force constants:

```bash
zstar bec pre --stru STRU
zstar bec run --dry-run
zstar bec run
zstar bec stat
zstar bec post
```

Then generate IR and Raman spectra from the completed response:

```bash
zstar spectra pre --root spectra --response .
zstar spectra run --root spectra
zstar spectra stat --root spectra
zstar spectra post --root spectra
```

`bec post` writes the BEC, BORN, force constants, and Gamma modes. IR uses the
mode frequencies and BEC; `spectra run` evaluates the additional PYATB
dielectric responses needed for Raman. Inputs and basis files remain in `run/`,
retained outputs are in `results/`, and the new calculation uses `work/`.
Archived spectra are available under `results/spectra/` in tabulated, PNG, PDF,
and SVG formats.

Once the stages are familiar, `bash run.sh --with-spectra` provides the same
resumable workflow. Add `--dry-run` to preview it without starting a solver.
The shared automatic-sign set has two physical displacements; the matched
Cartesian central set has twelve. Both also calculate `0.no-move`.

Compare full raw/projected Born tensors, the Gamma Hessian and optical triplet,
and the stable phonon dielectric response. See the parent README and benchmark
JSON for exact results and measured costs. This is a matched-setting numerical
equivalence test, not an accuracy claim against experiment.

The Unified result gives opposite Si/C diagonal BEC values of 2.70094 e and
three degenerate IR- and Raman-active optical modes at 772.645 cm^-1.
