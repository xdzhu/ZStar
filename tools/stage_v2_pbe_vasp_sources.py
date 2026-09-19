"""Stage small licensed inputs for the user's HF continuation, never DFT."""
import argparse
import json
from pathlib import Path
import shutil
import hashlib

parser = argparse.ArgumentParser()
parser.add_argument('--manifest', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
campaign = json.loads(args.manifest.read_text())
args.output.mkdir()  # refuse replacing an existing transfer
for material in ('gan','zno','pto','pzt001'):
    spec = campaign['cases'][material]
    source = Path(spec['vasp_reference'])
    target = args.output/material
    target.mkdir()
    hashes = {}
    for name in ('INCAR','KPOINTS','POTCAR','CONTCAR'):
        if not (source/name).is_file() or not (source/name).stat().st_size:
            raise ValueError(f'Missing continuation input: {source/name}')
        shutil.copy2(source/name, target/name)
        hashes[name] = hashlib.sha256((target/name).read_bytes()).hexdigest()
    (target/'source.json').write_text(json.dumps({
        'reference':str(source),'functional':'PBE',
        'expected_space_group':spec['expected_space_group'],
        'model_note':spec['model_note'],'source_sha256':hashes,
        'reference_accepted':False,'license':'User-owned compute input, not for publication'
    }, indent=2)+'\n')
