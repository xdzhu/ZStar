"""Retrieve public, checksum-verified isolated-chain reference data."""

import argparse
import hashlib
import json
from pathlib import Path

import requests


def fetch(output):
    session = requests.Session()
    session.trust_env = False
    base = 'https://data.mendeley.com/public-api/datasets/6tntvw37tr'
    folders = {
        'B3LYP-D3/structure': '06ef21d3-2f5d-4560-83c9-4567169eb20f',
        'HSE06-D3/structure': 'fd7661fa-56d4-4d10-b311-7658e60cb31f',
        'B3LYP-D3/gamma-point': 'f109b5f3-0fd7-45f4-85ce-f3931168f6f5',
    }
    manifest = {'doi': '10.17632/6tntvw37tr.1', 'license': 'CC BY 4.0',
                'author': 'Gianfranco Ulian', 'model': 'Nanorod', 'files': []}
    for relative, folder in folders.items():
        response = session.get(base + '/files', params={'folder_id': folder, 'version': 1},
                               headers={'Accept': 'application/vnd.mendeley-public-dataset.1+json'},
                               timeout=60)
        response.raise_for_status()
        for entry in response.json():
            name = entry['filename']
            if name.endswith('.png'):
                continue
            if Path(name).name != name:
                raise ValueError(f'Unexpected dataset filename: {name}')
            destination = output / relative / name
            details = entry['content_details']
            if destination.exists():
                data = destination.read_bytes()
            else:
                download = session.get(details['download_url'], timeout=120)
                download.raise_for_status()
                data = download.content
            digest = hashlib.sha256(data).hexdigest()
            if digest != details['sha256_hash']:
                raise ValueError(f'Checksum mismatch: {name}')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            manifest['files'].append({'path': str(destination.relative_to(output)),
                                      'url': details['download_url'], 'sha256': digest})
            print(destination, len(data), flush=True)
    (output / 'provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    fetch(parser.parse_args().output)
