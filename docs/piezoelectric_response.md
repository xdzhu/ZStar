# Bulk piezoelectric response

ZStar supports proper piezoelectric stress coefficients `e`, relaxed-ion
elastic coefficients `C`, and strain coefficients `d = e C^-1` for insulating
bulk crystals. Engineering Voigt order is `(xx, yy, zz, 2yz, 2xz, 2xy)`;
`e` is reported in C/m2, `C` in GPa, and `d` in pm/V (= pC/N).

## ABACUS + PYATB finite-strain route

The public Python API prepares one reference and central `+-0.5%` strains,
collects stress, forces, relaxed internal coordinates, and branch-matched
polarization, then fits the actual written strain vectors. Proper-response
corrections, point-group residuals, acoustic translation, elastic stability,
and the `e = d C` closure remain in the response record.

```python
from zstar.piezoelectric import prepare_abacus_strain_ensemble

prepare_abacus_strain_ensemble(
    "work",
    structure="run/STRU",
    input_template="run/INPUT",
    kpt_template="run/KPT",
    pp_dir="run",
    orb_dir="run",
    amplitude=0.005,
    ion_relaxation="relaxed-ion",
)
```

The helper scripts `tools/prepare_piezoelectric_case.py`,
`tools/run_piezoelectric_ensemble.sh`, and
`tools/collect_piezoelectric_case.py` provide the same lifecycle for repository
examples. Calculator execution is separate from response analysis so cluster
headers, modules, and resource requests remain site-controlled.

## Native VASP route

For LDA/GGA, ZStar keeps VASP's native electric and ionic response definitions:

```bash
zstar bec pre --calculator vasp --input-dir input --root response --piezo --elastic
zstar bec run --root response
zstar bec post --root response
```

`--piezo` requests relaxed-ion `e`; `--elastic` additionally obtains the bulk
elastic matrix and derives `d`. Licensed `POTCAR` data are not redistributed.
See [native VASP response](vasp_native_response.md) for solver and symmetry
details.

## Reproducible examples

[Wurtzite AlN](../examples/Piezoelectric_Response/AlN) and
[wurtzite ZnO](../examples/Piezoelectric_Response/ZnO) include clean ABACUS
inputs and assets, archived ABACUS + PYATB and native VASP tensors, literature
anchors, and self-checking `run.sh` files. Both use PBE and retain all tensor
components rather than only `d33`.

These workflows currently concern intrinsic bulk response. Vacuum-containing
slabs and wires require line/sheet electromechanical definitions and electrical
boundary conditions; ZStar does not silently report their supercell derivatives
as bulk piezoelectric coefficients.
