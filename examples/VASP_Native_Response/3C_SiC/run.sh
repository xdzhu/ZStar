#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$HERE"
: "${VASP_PSEUDO_ROOT:?Load your VASP environment and set VASP_PSEUDO_ROOT}"
command -v zstar >/dev/null
command -v vasp_std >/dev/null
MPI_TASKS=${MPI_TASKS:-${SLURM_NTASKS:-64}}
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export MKL_NUM_THREADS=1
LAUNCH=${VASP_COMMAND:-"mpirun -np $MPI_TASKS vasp_std"}
mkdir -p .work/relax .work/input results
for element in Si C; do
  test -s "$VASP_PSEUDO_ROOT/PBE/$element/POTCAR" || { echo "Missing PBE/$element/POTCAR" >&2; exit 2; }
done
if [[ ! -f .work/relax/vasp.log ]] || ! grep -q 'reached required accuracy' .work/relax/vasp.log; then
  cp run/INCAR run/POSCAR run/KPOINTS .work/relax/
  cat "$VASP_PSEUDO_ROOT/PBE/Si/POTCAR" "$VASP_PSEUDO_ROOT/PBE/C/POTCAR" > .work/relax/POTCAR
  echo "[STAGE] Relax primitive cell"
  (cd .work/relax && $LAUNCH > vasp.log 2>&1)
  grep -q 'reached required accuracy' .work/relax/vasp.log || { echo 'Relaxation did not converge' >&2; exit 3; }
  grep -Eq "running on +$MPI_TASKS +total cores" .work/relax/OUTCAR || { echo 'MPI rank count does not match allocation' >&2; exit 3; }
fi
cp .work/relax/CONTCAR .work/input/POSCAR
cp run/INCAR run/KPOINTS .work/input/
cp .work/relax/POTCAR .work/input/
cp .work/relax/CONTCAR results/SiC_relaxed.vasp
sha256sum .work/relax/INCAR .work/relax/POSCAR .work/relax/KPOINTS > results/stage_input_sha256.txt
for route in dfpt elastic; do
  root=.work/$route
  flag=--phonons
  [[ $route == elastic ]] && flag=--elastic
  if [[ ! -f $root/vasp_bec_manifest.json ]]; then
    zstar bec pre --calculator vasp --input-dir .work/input --root "$root" "$flag"
  fi
  echo "[STAGE] Native $route response"
  zstar bec run --root "$root" --omp-threads "$OMP_NUM_THREADS" --vasp-command "$LAUNCH"
  zstar bec post --root "$root"
  mkdir -p "results/$route"
  cp "$root"/vasp_native_response.json "$root"/vasp_bec.json "$root"/response.json \
    "$root"/BORN "$root"/BEC.raw.dat "$root"/qpoints.yaml "$root"/FORCE_CONSTANTS "results/$route/"
  cp "$root"/phonopy.yaml "$root"/irreps.yaml "results/$route/"
  cp -r "$root"/ir_spectrum "results/$route/"
  sha256sum "$root"/response/INCAR "$root"/response/POSCAR "$root"/response/KPOINTS \
    "$root"/response/POTCAR >> results/stage_input_sha256.txt
done
if [[ ! -f .work/raman/spectra_manifest.json ]]; then
  zstar spectra pre --calculator vasp --response .work/dfpt --root .work/raman
fi
echo '[STAGE] Native dielectric derivatives for Raman'
zstar spectra run --root .work/raman --omp-threads "$OMP_NUM_THREADS" --command "$LAUNCH"
zstar spectra post --root .work/raman
cp -r .work/raman/ir_spectrum .work/raman/raman_spectrum results/
cp .work/raman/spectra_results.json results/
cp .work/raman/qpoints.yaml results/
python verify_results.py
echo '[DONE] Native responses and mixed-route spectra are in results/'
