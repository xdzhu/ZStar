"""Reproduce retained Unified spectra without DFT, using the public kernels."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from zstar import spectra
from zstar.raman_response import reconstruct_raman_derivatives, project_raman_modes, internal_mode_indices
from zstar.shared_response import read_structure, make_phonopy, symmetry_operations
from zstar.response_units import raman_convention


def reproduce(case, output):
    inputs=case/'results/Unified/inputs'
    meta=json.loads((inputs/'manifest.json').read_text())
    for name,sha in meta['sha256'].items():
        if hashlib.sha256((inputs/name).read_bytes()).hexdigest()!=sha:
            raise ValueError(f'Changed archive input: {name}')
    atoms=read_structure(inputs/'STRU')
    modes=spectra.load_gamma_modes(inputs/'qpoints.yaml')
    np.testing.assert_allclose(atoms.cell,modes.lattice_angstrom,atol=1e-6,rtol=0)
    delta=np.asarray(atoms.scaled_positions)-modes.positions_fractional
    np.testing.assert_allclose((delta-np.rint(delta))@np.asarray(atoms.cell),0,atol=1e-6)
    dim=meta['dimension']
    observations=json.loads((inputs/'observations.json').read_text())
    tensors,diagnostics=reconstruct_raman_derivatives(len(atoms),observations,
        symmetry_operations(make_phonopy(atoms,symprec=meta['symprec_A']),dimension=dim))
    selected,audit=internal_mode_indices(modes,dim)
    numbers=(selected+1).tolist()
    factor={3:1.,2:modes.cell_height_angstrom,1:modes.area_angstrom2/(4*np.pi),0:modes.volume_angstrom3/(4*np.pi)}[dim]
    raman_tensors=project_raman_modes(tensors,modes.eigenvectors,modes.masses_amu)[selected]*factor
    common=dict(broadening_cm1=8,points=3001,allow_imaginary=True)
    raman=spectra.calculate_raman_spectrum(modes,numbers,raman_tensors,
        tensor_kind=raman_convention(dim)['tensor_unit'],temperature_K=298,laser_nm=532,**common)
    born=spectra.read_born_data(inputs/'BEC.dat',natoms=len(atoms),dielectric_path=inputs/'BORN')
    if dim==0:
        derivatives=spectra.mode_effective_charges(modes,born.tensors)[selected]*4.80320471257
        ir=spectra.calculate_molecular_ir_spectrum(modes,numbers,derivatives,**common)
        spectra.write_molecular_ir_outputs(output/'ir',ir)
    else:
        ir=spectra.calculate_ir_spectrum(modes,born,dimensionality=dim,mode_numbers=numbers,**common)
        spectra.write_ir_outputs(output/'ir',ir)
    spectra.write_raman_outputs(output/'raman',raman)
    np.save(output/'raman/atomic_dielectric_derivatives.npy',tensors)
    (output/'reconstruction.json').write_text(json.dumps(dict(
        source_manifest=meta,diagnostics=diagnostics,mode_selection=audit,
        raman_convention=raman_convention(dim),additional_DFT_calls=0),indent=2)+'\n')
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--case-dir',type=Path,required=True)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    print(reproduce(a.case_dir.resolve(),a.out or a.case_dir/'work-unified-post'))
