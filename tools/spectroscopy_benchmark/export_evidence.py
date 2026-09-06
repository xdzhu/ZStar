"""Archive compact benchmark evidence, never matrices or licensed inputs."""
import argparse
import json
from pathlib import Path
import tarfile

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = a.root.resolve()
names = {'STRU','shared_response.json','qpoints.yaml','phonopy.yaml','BORN','BEC.dat','component_times.jsonl',
         'completed.json','failed.json','source.json','Input','static_dielectric_function.dat',
         'static_dielectric_function.rounded.dat'}
names.update({'protocol.json','raman_manifest.json','raman_tensors.npy','mode_numbers.npy',
              'raman_modes.csv','raman_spectrum.dat','raman_tensors.json'})
with tarfile.open(a.output, 'w:gz') as t:
    for case in ('HfO2','MoS2','Sb2S3','CH4'):
        for scheme in ('unified','cartesian'):
            folder = root/case/scheme
            provenance = folder/'0.no-move/source.json'
            if not (folder/'phonopy.yaml').is_file() and provenance.is_file():
                original = Path(json.loads(provenance.read_text())['source']).parent/'phonopy.yaml'
                t.add(original, arcname=f'{case}/{scheme}/phonopy.yaml', recursive=False)
        for f in sorted((root/case).rglob('*')):
            if f.is_file() and f.name in names:
                t.add(f, arcname=f.relative_to(root).as_posix(), recursive=False)
print(a.output)
