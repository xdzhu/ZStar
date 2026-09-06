"""Capture runtime versions and code hashes without changing installed software."""
import argparse
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
from tools.spectroscopy_benchmark.run_optical_reuse import digest

p=argparse.ArgumentParser()
p.add_argument('--root',type=Path,required=True)
a=p.parse_args()
code=a.root/'code'
versions={}
for package in ['numpy','scipy','ase','phonopy','spglib','pyatb']:
    try:
        versions[package]=metadata.version(package)
    except metadata.PackageNotFoundError:
        versions[package]='Distribution metadata unavailable'
record=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
    packages=versions,code_sha256={str(p.relative_to(code)):digest(p)
        for folder in [code/'zstar',code/'tools/spectroscopy_benchmark']
        for p in sorted(folder.glob('*.py'))},
    ABACUS_executable='/home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus',
    ABACUS_new_control_parallelism='1 MPI x 40 OMP',PYATB_parallelism='40 MPI x 1 OMP')
(a.root/'runtime_record.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(versions,indent=2))
