"""Launch one explicitly selected post-processing worker, with detached I/O."""
import argparse
import json
from pathlib import Path
import socket
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
p.add_argument('--case', required=True)
p.add_argument('--attempt', type=int, default=1)
p.add_argument('--control', action='store_true')
p.add_argument('--part', type=int, default=1)
p.add_argument('--parts', type=int, default=1)
a = p.parse_args()
if socket.gethostname().split('.')[0] not in {'cu23','cu24','cu25','cu26'}:
    raise RuntimeError('Only the four user-authorized compute nodes may run this benchmark')
root = a.root.resolve()
suffix = '.control' if a.control else ''
if a.parts > 1:
    suffix += f'.part-{a.part}'
marker = root/f'{a.case}{suffix}.launch-{a.attempt}.json'
with marker.open('x') as f:
    with (root/f'{a.case}{suffix}.driver.log').open('ab') as log:
        command = ['bash',str(root/('run_control.sh' if a.control else 'run.sh')),a.case]
        if a.control:
            command += ['--part',str(a.part),'--parts',str(a.parts)]
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    json.dump(dict(host=socket.gethostname(), pid=process.pid, command=command),f)
print(marker.read_text())
