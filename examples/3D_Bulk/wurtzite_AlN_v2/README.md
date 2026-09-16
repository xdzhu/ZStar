# Wurtzite AlN — ZStar v2 3D piezoelectric benchmark

This case is the first **qualified research benchmark** for the v2 3D
homogeneous-strain response implementation. It uses bulk `P6_3mc` AlN with
`z || [0001]`, PBEsol, Dojo-NC-FR pseudopotentials, 8-au LCAO orbitals,
100 Ry and an `8x8x6` k mesh.

It validates a relaxed-ion, proper piezoelectric stress tensor `e`, the
relaxed-ion elastic tensor `C^E`, and the derived strain tensor
`d = e (C^E)^-1`. `e` and `d` are different constitutive forms: the present
result does not claim a device-mode coupling factor such as `k_p`.

## Fixed production protocol

New ensembles use the repository-wide fixed settings:

- engineering strain `eta = {-0.005, 0, +0.005}` for every independent
  direction; the zero geometry is shared, so a full six-direction audit has
  13 geometries, not 18 or 19;
- `symmetry_prec=1e-3`, reference `symmetry=1`, perturbed cells `symmetry=0`;
- `force_thr_ev=1e-4 eV/Angstrom`, `scf_thr=1e-8`, `relax_nmax=100`;
- one ABACUS calculation and one PYATB run per geometry; one PYATB run returns
  all three Cartesian polarization components.

The archived 2026-09-16 outputs were generated during development with the
same structure/Hamiltonian but over-tight response-stage inputs
`force_thr_ev=1e-6` and `scf_thr=1e-10`. The collector records those actual
values and separately applies the fixed `1e-4 eV/Angstrom` scientific force
acceptance gate. They are preserved as history, not advertised as the new
production defaults and not relabelled as `1e-4/1e-8` calculations.

## Results

The accepted `+-0.5%` values are:

| quantity | ZStar v2 | matched theory | difference |
|---|---:|---:|---:|
| `e31` (C/m2) | -0.63851 | -0.618 (PBEsol) | +3.32% in magnitude |
| `e33` (C/m2) | 1.54643 | 1.647 (PBEsol) | -6.11% |
| `e15` (C/m2) | -0.33511 | -0.374 (PBEsol) | -10.40% in magnitude |
| `d31` (pm/V) | -2.3975 | -2.1 (GGA, secondary) | +14.17% in magnitude |
| `d33` (pm/V) | 5.7350 | 5.4 (GGA, secondary) | +6.20% |
| `|d15|` (pm/V) | 3.0041 | 2.9 (GGA, secondary) | +3.59% |

The five independent elastic constants differ from the matched PBEsol
reference by 2.51--9.87%. The tensor is positive definite (minimum eigenvalue
111.525 GPa), all 13 stages remain insulating (minimum gap 4.109 eV), the
proper-`e` symmetry-projection relative residual is `1.47e-4`, and the elastic
projection relative residual is `1.12e-4`.

The developer-only `+-1%` calculation changes `e31/e33/e15` by only
0.048/0.057/0.014%, `d33` by 0.301%, and all listed elastic constants by at
most 0.214%. Combining the `+-0.5%` and `+-1%` values as a fourth-order
five-level derivative changes `e31/e33/e15` from the production central
difference by only 0.016/0.019/0.0047%. This confirms `+-0.5%` as the fixed
production amplitude; the five-level stencil remains a developer audit and is
not exposed as a user tuning parameter. Machine-readable details are in
`results/amplitude_audit.json`.

## Reproduction

`inputs/` contains the clean, relaxed reference structure and ABACUS templates.
Pseudopotential and orbital binaries are intentionally not redistributed; put
the files listed in `pseudopotentials/README.md` and `orbitals/README.md` in
those directories, then run:

```bash
./run.sh prepare
./run.sh submit
./run.sh status
./run.sh collect
```

The script submits one non-exclusive HF Slurm job with `32 MPI x 1 OMP` and
uses stage markers for restart. `submit` is explicit: preparation or status
inspection never launches a calculation. The `+-1%` audit is not generated
by this user reproduction path.

`results/summary.json` and `results/response_document.json` are the accepted
`+-0.5%` artifacts. `results/amplitude_1pct/` contains the development audit.
The source papers and exact comparison hierarchy are recorded in
`docs/v2_material_literature_comparison_20260916.md` and
`docs/v2_literature_sources.bib`.

This validates the present 3D hexagonal research API and result chain; it does
not by itself establish arbitrary-space-group, low-dimensional, finite-
temperature, flexoelectric, switching, or resonant-Raman support.
