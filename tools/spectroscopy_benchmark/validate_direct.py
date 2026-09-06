"""Compare absolute normal-mode response tensors, including degenerate gauges."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from zstar import spectra
from tools.spectroscopy_benchmark.atomic_raman import mode_derivatives


def placzek(tensors):
    t=(tensors+tensors.swapaxes(-1,-2))/2
    alpha=np.trace(t,axis1=-2,axis2=-1)/3
    traceless=t-alpha[:,None,None]*np.eye(3)
    return 45*alpha**2+7*1.5*np.sum(traceless**2,axis=(1,2))


def validate(root,case,repo):
    analysis=root/case/'analysis'
    report=json.loads((analysis/'comparison.json').read_text())
    matched = (root/case/'direct_control/completed.json').is_file()
    if case in ('HfO2','Sb2S3') and not matched:
        old=repo/'examples/IR_Raman_Spectra'/dict(
            HfO2='Bulk_HfO2/results/raman',Sb2S3='Nanowire_Sb2S3/results/Raman')[case]
        with (old/'raman_modes.csv').open() as f:
            rows=list(csv.DictReader(f))
        numbers=np.array([int(r['mode']) for r in rows])
        direct=np.load(old/'raman_tensors.npy')
        qpoints=(root/'legacy_HfO2/phonon_gamma/qpoints.yaml' if case=='HfO2'
                 else root/case/'unified/qpoints.yaml')
        modes=spectra.load_gamma_modes(qpoints)
        frequencies=np.array([float(r['frequency_cm-1']) for r in rows])
        np.testing.assert_allclose(frequencies,modes.frequencies_cm1[numbers-1],atol=1e-6)
    else:
        old=root/case/'direct_control'
        if not json.loads((old/'completed.json').read_text())['success']:
            raise ValueError('Direct calculation not complete')
        numbers=np.load(old/'mode_numbers.npy')
        direct=np.load(old/'raman_tensors.npy')
        modes=spectra.load_gamma_modes(root/case/'unified/qpoints.yaml')
        frequencies=modes.frequencies_cm1[numbers-1]
    # Use the old eigenvector gauge, not an arbitrary match of degenerate modes.
    derivative=np.load(analysis/'unified_atomic_derivatives.npy')
    projected=mode_derivatives(derivative,modes.eigenvectors,modes.masses_amu)[numbers-1]
    projected*=report['normalization_factor']
    a,b=placzek(projected),placzek(direct)
    result=dict(case=case,modes=numbers.tolist(),basis='Direct-control eigenvectors',
        absolute_tensor_relative_L2=float(np.linalg.norm(projected-direct)/np.linalg.norm(direct)),
        absolute_activity_relative_L2=float(np.linalg.norm(a-b)/np.linalg.norm(b)),
        activity_sum_ratio=float(a.sum()/b.sum()),
        maximum_tensor_component_difference=float(np.max(abs(projected-direct))),
        per_mode=[dict(mode=int(n),frequency_cm1=float(f),
            unified_activity=float(x),direct_activity=float(y),
            tensor_abs_L2=float(np.linalg.norm(u-d)))
            for n,f,x,y,u,d in zip(numbers,frequencies,a,b,projected,direct)],
        limitation=('Legacy HfO2 eigenvectors and 20-MPI timings reused; '
                    'not a same-parallelism end-to-end benchmark.' if case=='HfO2' and not matched else None))
    (analysis/'direct_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    np.savez(analysis/'direct_comparison.npz',numbers=numbers,frequencies=frequencies,
             unified_tensors=projected,direct_tensors=direct,
             unified_activity=a,direct_activity=b)
    print(json.dumps({k:v for k,v in result.items() if k not in ('per_mode','modes')},indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--repo',type=Path,default=Path.cwd())
    p.add_argument('--case',required=True)
    a=p.parse_args()
    validate(a.root,a.case,a.repo)
