"""Preserve a confirmed abandoned BN9 force attempt and resume remaining stages."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

ROOT=Path('/home/zhuxd/abacus/agent-runs/20260906-one-dimensional-benchmark')
case=ROOT/'independent_phonon/BN_9_0'
worker=json.loads((case/'worker.json').read_text())
if worker != {'host':'cu20','pid':31306,'status':'running'}:
    raise RuntimeError('Unexpected worker state; inspect before recovery')
probe=subprocess.run(['ssh','-o','ConnectTimeout=10','cu20','ps','-u','zhuxd','-o','pid=,args='],
                     capture_output=True,text=True,timeout=30,check=True)
if any('31306' in line or 'abacus' in line.lower() or 'one_dimensional_benchmark' in line
       for line in probe.stdout.splitlines()):
    raise RuntimeError('The old node may still contain live workers')
if len(list(case.glob('disp-*/completed.json'))) != 42:
    raise RuntimeError('Completed stage set changed; inspect before recovery')
stage=case/'disp-043'
if (stage/'completed.json').exists():
    raise RuntimeError('Interrupted stage has since completed')
recovery=case/'recovery'
recovery.mkdir(exist_ok=False)
stage.rename(recovery/stage.name)
stage.mkdir()
for path in (recovery/stage.name).iterdir():
    if path.is_file() and (path.name in ('STRU','INPUT','KPT') or path.suffix.lower() in ('.upf','.orb')):
        if path.is_symlink():
            raise RuntimeError('Unexpected input symlink')
        shutil.copy2(path,stage/path.name)
(case/'.worker.lock').rename(recovery/'abandoned-worker.lock')
shutil.copy2(case/'worker.json',recovery/'abandoned-worker.json')
record=dict(old_worker=worker,recovery_host=socket.gethostname(),
            completed_stages_preserved=42,interrupted_stage='disp-043',
            unrecorded_interrupted_attempts=1,interrupted_core_hours=None,
            old_node_process_probe=probe.stdout,
            cost_caveat='The old process disappeared before its timing finally block. '
                        'Successful-run costs exclude this unmeasured interruption; they are not total billed usage.')
(case/'recovery.json').write_text(json.dumps(record,indent=2)+'\n')
env={**os.environ,'PYTHONPATH':'/home/zhuxd/abacus/agent-runs/20260905-one-dimensional/upload',
     'OMP_NUM_THREADS':'40','MKL_NUM_THREADS':'40','OPENBLAS_NUM_THREADS':'1','I_MPI_PIN_DOMAIN':'omp'}
with (case/'resume-driver.log').open('xb') as log:
    child=subprocess.Popen([sys.executable,'-u',str(ROOT/'code/one_dimensional_benchmark.py'),
                            'run','BN_9_0','phonon'],env=env,stdin=subprocess.DEVNULL,
                           stdout=log,stderr=log,start_new_session=True)
(case/'resume-launch.json').write_text(json.dumps(dict(host=socket.gethostname(),pid=child.pid))+'\n')
print(json.dumps(dict(resumed_pid=child.pid,host=socket.gethostname(),remaining_SCFs=14)))
