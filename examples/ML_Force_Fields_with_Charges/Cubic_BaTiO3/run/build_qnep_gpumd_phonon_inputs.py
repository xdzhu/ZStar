"""Build a minimal GPUMD ``compute_phonon`` input for a trained qNEP model.

GPUMD supplies the qNEP forces and the finite-displacement force constants;
Phonopy subsequently applies the NAC using BECs dumped by the same qNEP model.
The five-atom primitive cell is replicated 2x2x2 (40 atoms), which is the
small compatibility cell used by this example.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", required=True, help="trained qNEP nep.txt filename")
    parser.add_argument("--a", type=float, default=4.04849223)
    parser.add_argument("--displacement", type=float, default=0.01)
    parser.add_argument("--replicate", type=int, default=2)
    args = parser.parse_args()
    target = Path(args.output).resolve()
    target.mkdir(parents=True, exist_ok=True)
    a = args.a
    positions = [
        ("Ba", 0.0, 0.0, 0.0),
        ("O", a / 2, a / 2, 0.0),
        ("O", a / 2, 0.0, a / 2),
        ("O", 0.0, a / 2, a / 2),
        ("Ti", a / 2, a / 2, a / 2),
    ]
    lattice = " ".join(f"{x:.12g}" for x in (a, 0, 0, 0, a, 0, 0, 0, a))
    lines = [
        str(len(positions)),
        f'Lattice="{lattice}" Properties=species:S:1:pos:R:3:force:R:3 energy=0.0 pbc="T T T"',
    ]
    lines.extend(f"{s} {x:.12g} {y:.12g} {z:.12g} 0 0 0" for s, x, y, z in positions)
    (target / "model.xyz").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (target / "kpoints.in").write_text(
        "0 0 0 G\n0.5 0 0 X\n0.5 0.5 0 M\n0 0 0 G\n0.5 0.5 0.5 R\n0.5 0 0 X\n",
        encoding="utf-8",
    )
    (target / "run.in").write_text(
        f"replicate {args.replicate} {args.replicate} {args.replicate}\n"
        f"potential {Path(args.model).name}\n"
        "dump_xyz 1 equilibrium_qnep.xyz precision double force bec\n"
        "velocity 1\nensemble nve\ntime_step 0\nrun 1\n"
        f"compute_phonon {args.displacement:.12g}\n",
        encoding="utf-8",
    )
    (target / "manifest.json").write_text(
        "{\n"
        '  "schema": "zstar-trained-qnep-gpumd-phonon-inputs",\n'
        f'  "model": "{Path(args.model).name}",\n'
        f'  "cell": "cubic BaTiO3 primitive 5 atoms, {args.replicate}x{args.replicate}x{args.replicate} GPUMD cell",\n'
        f'  "replicate": [{args.replicate}, {args.replicate}, {args.replicate}],\n'
        f'  "lattice_A": {a:.12g},\n'
        f'  "displacement_A": {args.displacement:.12g},\n'
        '  "nac": "Phonopy BORN from GPUMD dump_xyz bec; GPUMD compute_phonon supplies force constants"\n'
        "}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
