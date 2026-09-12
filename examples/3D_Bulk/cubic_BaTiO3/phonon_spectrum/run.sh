#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WORK=${ZSTAR_WORK:-"$ROOT/work"}
if [[ ! -d "$WORK" ]]; then
  mkdir -p "$WORK"
  cp -a "$ROOT/run/." "$WORK/"
fi
if [[ ! -s "$WORK/BORN" ]]; then
  cp "$ROOT/../results/unified/BORN" "$WORK/BORN"
fi
cd "$WORK"

zstar phonon pre --spectrum --stru STRU --supercell "2 2 2" --physical-dim 3
zstar phonon run --root .
zstar phonon post --root . --stru STRU --physical-dim 3
zstar phonon spectrum --root . --nac --band-only --omit-disconnected-tail

mkdir -p "$ROOT/results"
cp phonon_spectrum.json phonon_spectrum_result.json "$ROOT/results/"
cp phonopy.yaml FORCE_SETS BORN "$ROOT/results/"
cp phonon_band_dos_*.pdf phonon_band_dos_*.png "$ROOT/results/"
cp phonon_band_nac_comparison.pdf phonon_band_nac_comparison.png "$ROOT/results/"
echo "Results written to $ROOT/results"
