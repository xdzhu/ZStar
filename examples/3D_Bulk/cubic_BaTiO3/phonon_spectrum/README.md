# Cubic BaTiO3: phonon dispersion and NAC

This example adds an on-demand finite-wave-vector phonon calculation to the
cubic BaTiO3 BEC archive. It uses the same PBEsol settings and BORN file as
the parent BEC example. The clean `run/` directory contains only the ABACUS
input files and the required pseudopotentials/orbitals; computed data belong
to `results/`.

The example explicitly uses a `2 2 2` supercell to keep the demonstration
tractable. Without `--supercell`, ZStar chooses a diagonal repeat that makes
each periodic lattice vector strictly longer than 10 Angstrom. The workflow
uses Phonopy to generate displacements and to collect force constants, then
uses a Seekpath path backed by spglib to label the standardized high-symmetry
route.

## Step-by-step

Configure ABACUS in the active environment, then run from this directory:

```bash
zstar phonon pre --spectrum --stru STRU --input INPUT --root run \
  --supercell "2 2 2" --physical-dim 3
zstar phonon run --root run
zstar phonon post --root run --stru STRU --physical-dim 3
cp ../results/unified/BORN run/BORN
zstar phonon spectrum --root run --nac --band-only --omit-disconnected-tail
```

To additionally write a compact band-only comparison for a manuscript, use:

```bash
zstar phonon spectrum --root run --nac --band-only
```

The same sequence is available as `bash run.sh`; that script creates an
isolated `work/` directory and does not modify `run/` or the archived results.
The command after `phonon post` requires the BORN file produced by a completed
BEC calculation. The bundled BORN is supplied for convenience and is copied
as a regular file; no density or cube file is linked into the calculation.

## Outputs

`zstar phonon spectrum` writes three vector plots by default when BORN is
available. The frequency axis is in THz, and the plotted range is
`-8` to `25 THz`.

| File | Meaning |
| --- | --- |
| `phonon_band_dos_wo_nac.pdf` | phonon bands and DOS without NAC |
| `phonon_band_dos_with_nac.pdf` | phonon bands and DOS with bulk NAC |
| `phonon_band_dos_nac_comparison.pdf` | blue/red overlay comparison |
| `phonon_band_nac_comparison.pdf` | optional band-only blue/red comparison |

PNG previews, `phonon_spectrum_result.json`, the selected path labels, and
the raw Phonopy `FORCE_SETS` and `phonopy.yaml` are also written. The force
constants remain in Phonopy's YAML archive so that its primitive-to-supercell
mapping is preserved. The red curves in the comparison plot are drawn after the blue
curves, so an unchanged branch remains visibly overlapped.

NAC is deliberately restricted to a three-dimensional bulk response in this
workflow. ZStar reports a clear error rather than applying a bulk Coulomb
correction to a slab, nanowire, or molecule.
