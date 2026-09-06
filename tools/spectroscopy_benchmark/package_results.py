"""Export small, hash-checked observations; retain no electronic matrices."""
import importlib.util
import json
from pathlib import Path
import shutil
import numpy as np
from zstar.shared_abacus import _digest
from zstar.shared_response import actual_displacement,read_structure

repo=Path(__file__).resolve().parents[2]
cases={'HfO2':'Bulk_HfO2','MoS2':'2D_MoS2','Sb2S3':'Nanowire_Sb2S3','CH4':'Molecule_CH4'}
spec=importlib.util.spec_from_file_location('replot',repo/'examples/common/reproduce_unified_spectra.py')
replot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(replot)
summary=json.loads((repo/'docs/research/unified_spectroscopy_20260906/summary.json').read_text())
for case,name in cases.items():
    source=repo/'docs/research/unified_spectroscopy_20260906/evidence'/case/'unified'
    target=repo/'examples/IR_Raman_Spectra'/name
    folder=target/'results/Unified/inputs'
    folder.mkdir(parents=True,exist_ok=True)
    for f in ('STRU','qpoints.yaml','phonopy.yaml','BORN','BEC.dat'):
        shutil.copy2(source/f,folder/f)
    meta=json.loads((source/'shared_response.json').read_text())
    reference=np.array(json.loads((source/'0.no-move/completed.json').read_text())['epsilon'])
    atoms=read_structure(source/'STRU')
    observations=[]
    for s in meta['stages']:
        atom,vector=actual_displacement(atoms,read_structure(source/s['name']/'STRU'))
        assert atom==s['atom']
        np.testing.assert_allclose(vector,s['displacement_A'],atol=1e-10,rtol=0)
        record=json.loads((source/s['name']/'completed.json').read_text())
        assert record['success'] and record['additional_DFT_calls']==0
        observations.append(dict(atom=atom,displacement_A=vector.tolist(),
            delta_epsilon=(np.array(record['epsilon'])-reference).tolist()))
    (folder/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
    portable=dict(schema='zstar-example-unified-observations',version=1,
        case=case,dimension=meta['dimension'],symprec_A=meta['symprec_A'],
        source_ensemble_sha256=_digest(source/'shared_response.json'),
        source='docs/research/unified_spectroscopy_20260906/evidence/'+case+'/unified',
        sha256={f.name:_digest(f) for f in folder.iterdir() if f.name!='manifest.json'})
    (folder/'manifest.json').write_text(json.dumps(portable,indent=2)+'\n')
    replot.reproduce(target,target/'results/Unified')
    record=next(r for r in summary['records'] if r['case']==case)
    (target/'results/Unified/efficiency.json').write_text(json.dumps(record,indent=2)+'\n')
    print(case,'packaged')
