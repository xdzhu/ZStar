"""Prepare comparison inputs using the revised ZStar CLI."""
import json
from pathlib import Path
import subprocess
import sys

states = json.loads(Path('mesh_gaps.json').read_text())['systems']
for name, candidate in [('initial', 'h0.csr'), ('predicted', 'predicted.csr')]:
    state = states[name]
    if state['indirect_gap_eV'] < 0.02:
        print(f'{name}: sampled occupied and empty energies lack the gap required for Berry phase')
        continue
    subprocess.run([sys.executable, '-m', 'zstar', 'response', 'pyatb-hamiltonian',
                    '--model', 'nextham', '--input', 'Input.template', '--hamiltonian', candidate,
                    '--structure', 'STRU', '--prediction-structure', 'STRU', '--fermi-energy',
                    str(state['fermi_eV']), '--output-dir', name], check=True)
