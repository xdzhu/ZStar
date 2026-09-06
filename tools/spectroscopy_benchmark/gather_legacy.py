"""Read-only compact provenance export for the retained HfO2 normal-mode route."""
import argparse
import json
from pathlib import Path
import re
import tarfile
from tools.spectroscopy_benchmark.run_optical_reuse import digest

p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
root=Path('/home/zhuxd/abacus/zstar_validation/hfo2_pbesol_tzdp9_20260901')
stages=sorted((root/'phonon_gamma').glob('raman_*/mode-*/plus'))
stages+=sorted((root/'phonon_gamma').glob('raman_*/mode-*/minus'))
rows=[]
with tarfile.open(a.output,'w:gz') as archive:
    for path in [root/'phonon_gamma/qpoints.yaml',root/'phonon_gamma/phonopy.yaml',
                 root/'bec/0.no-move/STRU',root/'bec/0.no-move/INPUT-scf',
                 root/'bec/0.no-move/KPT']:
        archive.add(path,arcname='legacy_HfO2/'+path.relative_to(root).as_posix())
    for stage in stages:
        timing=stage/'time.json'
        running=stage/'pyatb/Out/running.log'
        total=re.findall(r'Total time\s*:\s*(\d+) h (\d+) m (\d+) s',running.read_text())
        if len(total)!=1:
            raise ValueError(f'Missing/ambiguous PYATB timer: {running}')
        hours,minutes,seconds=map(int,total[0])
        row=dict(stage=str(stage),ABACUS_wall_s=json.loads(timing.read_text())['total'],
                 PYATB_wall_s=hours*3600+minutes*60+seconds,mpi=20,omp=1,
                 time_sha256=digest(timing),PYATB_log_sha256=digest(running))
        rows.append(row)
        for path in [timing,running,stage/'pyatb/Input',stage/'INPUT']:
            archive.add(path,arcname='legacy_HfO2/'+path.relative_to(root).as_posix())
report=dict(rows=rows,SCF_calls=len(rows),
    ABACUS_core_h=sum(r['ABACUS_wall_s'] for r in rows)*20/3600,
    PYATB_core_h=sum(r['PYATB_wall_s'] for r in rows)*20/3600,
    caveat='Solver-internal timers, not wrapper wall times. PYATB rounded to seconds. '
           'Legacy parallelism 20 MPI x 1 OMP differs from new 40-core controls.')
a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
