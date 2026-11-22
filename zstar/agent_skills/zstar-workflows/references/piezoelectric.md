# Piezoelectric-response workflow

Use this lane only for insulating three-dimensional crystals. Confirm the
reference phase, polar-axis orientation, and engineering Voigt convention
before comparing tensor components.

## VASP-native route

For LDA/GGA, preserve the calculator-native response definitions:

```bash
zstar piezo pre --calculator vasp --input-dir input --root response
zstar piezo run --root response
zstar piezo post --root response
```

The dedicated family obtains the relaxed-ion piezoelectric stress tensor, the
relaxed-ion elastic tensor, and permits `d = e C^-1`. Check
the electronic/ionic closure, elastic symmetry and positive definiteness, and
the back-conversion `e = d C`. Do not replace this route with the ABACUS finite-
strain solver when the user selected VASP.

The lower-level `zstar bec ... --piezo [--elastic]` switches remain available
for compatibility.

## ABACUS + PYATB finite-strain route

Use `zstar.piezoelectric.prepare_abacus_strain_ensemble` or the reproduction
scripts under `examples/Piezoelectric_Response`. The fixed production protocol
uses central `+-0.5%` engineering strains, `scf_thr=1e-8`, and a fixed-cell
force threshold of `1e-4 eV/Angstrom`. Keep the reference plus all 12 signed
strain stages and use the actual written cell matrices in the fit.

Run calculator stages only after inspecting the prepared inputs and site
allocation. Collect with `tools/collect_piezoelectric_case.py`, then inspect
branch matching, fit rank, point-group residuals, acoustic translation,
elastic eigenvalues, and `e = d C` closure. A completed calculation is not an
external validation until its phase, functional, tensor convention, and
literature source have also been checked.

The curated AlN and ZnO cases provide accepted examples. GaN has a larger
cross-backend difference, tetragonal PbTiO3 remains cross-route conditional,
and the incomplete PZT ensemble must not be presented as a completed result.
