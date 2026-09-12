# Finite-q phonon dispersion and NAC

The Unified BEC workflow supplies the zone-center force constants and a
Phonopy-compatible `BORN` file. Use `zstar phonon spectrum` when a finite-q
phonon band structure and phonon DOS are required. This is a separate
supercell calculation; it does not repeat the Unified Gamma-point BEC SCFs.

## Workflow

Prepare a directory containing `STRU`, `KPT`, an ABACUS input with `cal_force 1`,
and the ABACUS pseudopotentials/orbitals. By default the input is `INPUT`; a
user-supplied CPU or GPU input can be selected explicitly:

```bash
zstar phonon pre --spectrum --root . --stru STRU --input INPUT --physical-dim 3
zstar phonon run --root .
zstar phonon stat --root .
zstar phonon post --root . --stru STRU --physical-dim 3
```

`--input` does not rewrite or normalize the source file. It only stages the
selected file as `INPUT` in each displacement directory, so calculator-specific
settings such as a GPU `ks_solver` remain under the user's control. The input
must enable `cal_force 1` because Phonopy collects forces from these runs.

For a 3D bulk calculation, a typical allocation uses `OMP_NUM_THREADS=1` and
the available CPU cores as MPI ranks. A low-dimensional or molecular case may
instead benefit from fewer MPI ranks and more OpenMP threads. ZStar leaves this
choice to the user's scheduler header and execution configuration.

If `--supercell` is omitted, each periodic lattice vector is repeated until
its length is strictly greater than 10 Angstrom. To choose the repeats
explicitly, use for example `--supercell "2 2 2"`. Seekpath generates the
standardized high-symmetry path and uses spglib symmetry data for the labels.

For a polar bulk material, copy the `BORN` file produced by `zstar bec post`
into the phonon directory and run:

```bash
cp path/to/bec/BORN .
zstar phonon spectrum --root . --nac
```

For a compact manuscript-style comparison containing only the two band sets,
add `--band-only`:

```bash
zstar phonon spectrum --root . --nac --band-only
```

For a path whose final branch is disconnected from the main route, add
`--omit-disconnected-tail` to omit that trailing branch. This is useful for
focused LO-TO splitting figures, but is not enabled by default:

```bash
zstar phonon spectrum --root . --nac --band-only --omit-disconnected-tail
```

The default output is three vector plots. The phonon-frequency axis is reported
in THz, which is the native frequency unit of the Phonopy archive used by this
workflow. The plotted frequency range is fixed to `-8` to `25 THz` so small
imaginary frequencies remain visible without making the figure too compact.

| File | Content |
| --- | --- |
| `phonon_band_dos_wo_nac.pdf` | Bands and DOS without the non-analytic correction |
| `phonon_band_dos_with_nac.pdf` | Bands and DOS with the bulk NAC |
| `phonon_band_dos_nac_comparison.pdf` | Blue/red overlay comparison |
| `phonon_band_nac_comparison.pdf` | Optional band-only blue/red comparison |

PNG previews and `phonon_spectrum_result.json` are written alongside the PDFs.
The JSON records the standardized space group, labels, q-point path, DOS mesh,
and output names. `--no-nac` writes only the w/o NAC plot. NAC is restricted to
three-dimensional bulk calculations with a compatible `BORN` file; it is not a
bulk approximation for slabs, nanowires, or molecules.

## Included example

The complete cubic BaTiO3 case is in
`examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/`. Its `run/` directory is a
clean input set, `results/` contains the verified archive and plots, and
`run.sh` executes the same steps in an isolated working directory.
