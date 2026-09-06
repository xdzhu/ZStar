"""Evidence-linked cost accounting and common-scale spectroscopy overlays."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from zstar import spectra
from tools.spectroscopy_benchmark.collect import optical_indices
from tools.spectroscopy_benchmark.run_optical_reuse import digest

CASES=['HfO2','MoS2','Sb2S3','CH4']
KEYS={'HfO2':'t_HfO2','MoS2':'MoS2','Sb2S3':'Sb2S3','CH4':'CH4'}


def ir_data(root,case):
    curves=[]
    modes_all=[]
    charges=[]
    dimension=json.loads((root/case/'unified/shared_response.json').read_text())['dimension']
    for scheme in ('unified','cartesian'):
        folder=root/case/scheme
        modes=spectra.load_gamma_modes(folder/'qpoints.yaml')
        selected=optical_indices(modes,dimension)
        if np.any(modes.frequencies_cm1[selected]<=0):
            raise ValueError('Unstable internal IR modes')
        born=spectra.read_born_data(folder/'BEC.dat',natoms=len(modes.masses_amu))
        effective=spectra.mode_effective_charges(modes,born.tensors)[selected]
        curves.append((modes.frequencies_cm1[selected],np.sum(effective**2,axis=1)))
        modes_all.append(modes)
        charges.append(born.tensors)
    selected=optical_indices(modes_all[0],dimension)
    z=[spectra.mode_effective_charges(modes_all[0],c)[selected] for c in charges]
    result=dict(mode_charge_relative_L2_common_basis=float(np.linalg.norm(z[0]-z[1])/np.linalg.norm(z[1])),
                maximum_sorted_frequency_difference_cm1=float(np.max(abs(curves[0][0]-curves[1][0]))))
    grid=np.linspace(0,max(np.max(c[0]) for c in curves)+40,4001)
    y=[spectra._lorentzian(grid,f,8)@a for f,a in curves]
    scale=max(np.max(a) for a in y)
    np.savez(root/case/'analysis/ir_comparison.npz',frequency=grid,
             unified=y[0]/scale,cartesian=y[1]/scale,
             unified_frequencies=curves[0][0],cartesian_frequencies=curves[1][0],
             unified_oscillator_strengths=curves[0][1],cartesian_oscillator_strengths=curves[1][1])
    return result


def build(root,out,repo):
    out.mkdir(parents=True,exist_ok=True)
    basepath=repo/'docs/research/separate_unified_efficiency.json'
    base_document=json.loads(basepath.read_text())
    baseline=base_document['cases']
    records=[]
    def source_key(path):
        try:
            return path.resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            return str(path.resolve())
    provenance={source_key(basepath):digest(basepath)}
    for case in CASES:
        path=root/case/'analysis/comparison.json'
        fit=json.loads(path.read_text())
        directpath=root/case/'analysis/direct_comparison.json'
        direct=json.loads(directpath.read_text())
        provenance[source_key(path)]=digest(path)
        provenance[source_key(directpath)]=digest(directpath)
        b=baseline[KEYS[case]]
        if case=='Sb2S3':
            source=repo/'examples/IR_Raman_Spectra/Nanowire_Sb2S3/results/compute_costs.json'
            costs=json.loads(source.read_text())['raman']
            raman=costs['ABACUS']+costs['PYATB']
            scfs=52
        elif case=='HfO2' and not (root/case/'direct_control/completed.json').is_file():
            source=root/'legacy_HfO2.tar.json'
            costs=json.loads(source.read_text())
            raman=costs['ABACUS_core_h']+costs['PYATB_core_h']
            scfs=costs['SCF_calls']
        else:
            source=root/case/'direct_control/component_times.jsonl'
            costs=[json.loads(s) for s in source.read_text().splitlines()]
            raman=sum(r['allocated_core_hours'] for r in costs if r['success'] and r['kind'] in ('ABACUS','PYATB'))
            scfs=sum(r['success'] and r['kind']=='ABACUS' for r in costs)
            if scfs!=2*len(direct['modes']):
                raise ValueError('Control SCF accounting mismatch')
        provenance[source_key(source)]=digest(source)
        incremental=fit['unified']['optical_increment_core_h']+fit['unified']['precision_reference_core_h']
        old=b['core_h_Separate']+raman
        new=b['core_h_Unified']+incremental
        records.append(dict(case=case,dimension=fit['dimension'],
            IR_SCF_old=b['SCF_Separate'],IR_SCF_unified=b['SCF_Unified'],
            IR_core_h_old=b['core_h_Separate'],IR_core_h_unified=b['core_h_Unified'],
            IR_speedup=b['speedup'],Raman_mode_SCF_old=scfs,Raman_extra_SCF_unified=0,
            full_SCF_old=b['SCF_Separate']+scfs,full_SCF_unified=b['SCF_Unified'],
            old_mode_Raman_core_h=raman,new_static_postprocessing_core_h=incremental,
            full_core_h_old=old,full_core_h_unified=new,assembled_speedup=old/new,
            parallelism_matched=case!='HfO2' or (root/case/'direct_control/completed.json').is_file(),
            Raman_atomic_Cartesian_tensor_error=fit['optical_mode_tensor_relative_difference'],
            Raman_direct_tensor_error=direct['absolute_tensor_relative_L2'],
            Raman_direct_activity_error=direct['absolute_activity_relative_L2'],
            IR_validation=ir_data(root,case)))
    spending={}
    for case in CASES:
        successful=failed=preparation=0.
        for file in (root/case).glob('*/component_times.jsonl'):
            for line in file.read_text().splitlines():
                row=json.loads(line)
                cost=row.get('core_hours',row.get('allocated_core_hours'))
                if row.get('kind')=='preparation':
                    preparation+=cost
                elif row['success']:
                    successful+=cost
                else:
                    failed+=cost
        spending[case]=dict(successful_solver_core_h=successful,failed_solver_core_h=failed,
                            preparation_allocated_core_h=preparation)
    result=dict(scope='Primitive-cell Gamma nonresonant Placzek IR/Raman; fixed relaxed geometry',
        accounting='Assembled measured components, not newly timed full workflows. Relaxation excluded. '
        'ABACUS+PYATB only; preparation excluded. Extra precision reference included conservatively. '
        'Reused-matrix PYATB timers include read-only provenance/hash checks. '
        'Cartesian optical reconstruction is verification cost, not new production cost. '
        'Old Raman computes both signs for all nonrigid modes, not a maximally symmetry-reduced mode baseline.',
        HfO2_caveat=None if records[0]['parallelism_matched'] else
        'Legacy Raman 20 MPI x 1 OMP solver timers; new route 40 cores. Contextual comparison only.',
        retained_BEC_baseline_caveat=base_document['caveat'],
        records=records,new_campaign_spending=spending,source_sha256=provenance,
        analysis_code_sha256={p.name:digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))})
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    columns=[key for key in records[0] if key!='IR_validation']
    with (out/'efficiency.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)
    lines=['# Unified spectroscopy: bounded four-dimensional benchmark','',
           result['accounting'],'',result['HfO2_caveat'] or 'All four pairs use matched 40-core profiles.','',
           result['retained_BEC_baseline_caveat'],'',
           '| System | IR SCFs: old/new | IR speedup | IR+Raman SCFs: old/new | Old core-h | New core-h | Ratio |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for r in records:
        lines.append(f"| {r['case']} | {r['IR_SCF_old']}/{r['IR_SCF_unified']} | {r['IR_speedup']:.2f} | "
            f"{r['full_SCF_old']}/{r['full_SCF_unified']} | {r['full_core_h_old']:.2f} | "
            f"{r['full_core_h_unified']:.2f} | {r['assembled_speedup']:.2f}{'*' if not r['parallelism_matched'] else ''} |")
    lines+=['','HfO2 uses the completed matched control; its legacy 20-MPI result remains historical evidence.','',
            '| System | Atomic Cartesian tensor difference | Direct-mode tensor difference | Direct-mode absolute activity difference |',
            '|---|---:|---:|---:|']
    for r in records:
        lines.append(f"| {r['case']} | {100*r['Raman_atomic_Cartesian_tensor_error']:.4g}% | "
                     f"{100*r['Raman_direct_tensor_error']:.4g}% | {100*r['Raman_direct_activity_error']:.4g}% |")
    lines+=['','| System | IR mode-charge difference (common basis) | Maximum optical-frequency difference (cm^-1) |',
            '|---|---:|---:|']
    for r in records:
        ir=r['IR_validation']
        lines.append(f"| {r['case']} | {100*ir['mode_charge_relative_L2_common_basis']:.4g}% | "
                     f"{ir['maximum_sorted_frequency_difference_cm1']:.4g} |")
    lines+=['','Differences are relative L2 norms over all selected modes, not per-mode relative errors. '
            'Near-zero forbidden modes are retained. No independent curve normalization is used in the overlays.',
            '', 'IR overlays use each route\'s own Gamma frequencies. Raman overlays use the direct-control '
            'eigenbasis and frequencies to isolate the response-derivative comparison; they do not independently '
            'validate the phonon frequencies. Raw oscillator strengths, tensors, and activities accompany the curves.',
            '', 'CH4: six rigid motions are identified by mass-weighted overlaps; numerical rotational '
            'negative modes are recorded, not erased. Only positive internal vibrations enter these spectra.',
            '', 'No old relaxation/BEC/phonon SCF was repeated. New DFT: only 12 MoS2 + 18 CH4 '
            '+ 30 HfO2 missing matched conventional Raman controls. Unified Raman reuses matrices with zero extra DFT.',
            '', 'Do not extrapolate these timings to resonant Raman, supercell phonon dispersion, '
            'or all materials. The reconstruction kernel is now part of the public Unified spectra lifecycle; '
            'see ../../unified_spectroscopy.md for reproducible commands.']
    (out/'README.md').write_text('\n'.join(lines)+'\n')
    return result


def draw(root,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'Arial','font.size':10,'svg.fonttype':'none',
        'pdf.fonttype':42,'axes.linewidth':.8,'xtick.direction':'in','ytick.direction':'in',
        'xtick.top':True,'ytick.right':True,'legend.frameon':False})
    fig,axes=plt.subplots(4,2,figsize=(7.4,9.2),layout='constrained')
    labels=['t-HfO$_2$ (3D)','MoS$_2$ (2D)','Sb$_2$S$_3$ (1D)','CH$_4$ (0D)']
    for row,(case,label) in enumerate(zip(CASES,labels)):
        ir=np.load(root/case/'analysis/ir_comparison.npz')
        direct=np.load(root/case/'analysis/direct_comparison.npz')
        f=direct['frequencies']
        grid=np.linspace(0,f.max()+40,4001)
        prefactor=np.maximum(1e7/532-f,0)**4*(1+1/np.expm1(1.438776877*f/298))/f
        y=[spectra._lorentzian(grid,f,8)@(direct[k]*prefactor)
           for k in ('unified_activity','direct_activity')]
        scale=max(a.max() for a in y)
        for col,ax in enumerate(axes[row]):
            x=ir['frequency'] if col==0 else grid
            new,old=(ir['unified'],ir['cartesian']) if col==0 else (y[0]/scale,y[1]/scale)
            ax.plot(x,old,color='.60',lw=2.4,label='Cartesian' if col==0 else 'Mode FD')
            ax.plot(x,new,color='#C43F42' if col==0 else '#246CB0',lw=1.15,ls='--',label='Unified')
            ax.set(xlim=(0,x[-1]),ylim=(0,1.36),xlabel=r'Wavenumber (cm$^{-1}$)',
                   ylabel='IR intensity (a.u.)' if col==0 else 'Raman intensity (a.u.)')
            ax.set_yticks([0,.5,1])
            ax.text(.02,.96,f'({chr(97+2*row+col)})',transform=ax.transAxes,va='top',fontsize=11)
            ax.legend(loc='upper right',fontsize=8.4,ncol=2,handlelength=1.6,columnspacing=.8)
            if col==0:
                ax.set_title(label,fontsize=10.5,loc='left',pad=7)
    for ext in ('pdf','svg','png'):
        fig.savefig(out/f'Spectroscopy_Unified_Benchmark.{ext}',dpi=350)
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--repo',type=Path,default=Path.cwd())
    a=p.parse_args()
    build(a.root,a.out,a.repo)
    draw(a.root,a.out)
