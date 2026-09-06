"""Count inputs at each manuscript BEC geometry; do not infer completed DFT."""
import hashlib
import json
from pathlib import Path
import tarfile

import numpy as np
import spglib
from zstar.shared_response import read_structure, make_phonopy, DEFAULT_DISTANCE

ROOT = Path(__file__).resolve().parents[2]


def main():
    configs = [
        ('cubic_BaTiO3', 'examples/3D_Bulk/cubic_BaTiO3/results/unified/STRU', 3, 'PBEsol', 18, 'central'),
        ('t_HfO2', 'docs/paper_figures/source_data/hfo2/STRU', 3, 'PBEsol', 12, 'central'),
        ('hBN', 'examples/2D_Slab/hBN/run/STRU', 2, 'PBE', 12, 'central'),
        ('alpha_In2Se3', 'examples/2D_Slab/In2Se3_PBEsol/results/STRU', 2, 'PBEsol+D3(0)', 30, 'central'),
        ('BN_9_0', 'examples/IR_Raman_Spectra/Nanotube_BN_9_0/results/STRU', 1, 'PBE', 60, 'central'),
        ('Sb2S3', 'examples/IR_Raman_Spectra/Nanowire_Sb2S3/results/STRU', 1, 'PBE+D3(BJ)', 30, 'central'),
        ('H2O', 'examples/0D_Molecules/H2O/run/STRU', 0, 'PBE', 12, 'central'),
        ('CH4', 'examples/0D_Molecules/CH4/run/STRU', 0, 'PBE', 12, 'central'),
    ]
    rows = []
    gate_sources = {
        'cubic_BaTiO3': 'examples/3D_Bulk/cubic_BaTiO3/results/unified/0.no-move/zstar_insulation.json',
        't_HfO2': 'docs/paper_figures/source_data/hfo2/provenance.json',
        'hBN': 'examples/2D_Slab/hBN/results/0.no-move/zstar_insulation.json',
        'alpha_In2Se3': 'examples/2D_Slab/In2Se3_PBEsol/results/0.no-move/zstar_insulation.json',
        'BN_9_0': 'examples/IR_Raman_Spectra/Nanotube_BN_9_0/results/native_evidence.tar.gz',
        'Sb2S3': 'examples/IR_Raman_Spectra/Nanowire_Sb2S3/results/native_evidence.tar.gz',
        'H2O': 'examples/0D_Molecules/H2O/results/PBE_APT/zstar_insulation.json',
        'CH4': 'examples/0D_Molecules/CH4/results/PBE_APT/zstar_insulation.json',
    }
    for name, path, dim, xc, old, method in configs:
        atoms = read_structure(ROOT/path)
        ph = make_phonopy(atoms)
        ph.generate_displacements(distance=DEFAULT_DISTANCE, is_plusminus='auto')
        data = spglib.get_symmetry_dataset((atoms.cell, atoms.scaled_positions, atoms.numbers), symprec=1e-5)
        expected = len(np.unique(data.equivalent_atoms)) * 3 * (2 if method=='central' else 1)
        if old != expected:
            raise ValueError(f'{name}: prepared count {old} does not match geometry count {expected}')
        row = dict(system=name, structure=path, structure_sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
                   dimension=dim, xc=xc, space_group=data.international, point_group=data.pointgroup,
                   cartesian_method=method, cartesian_displacements=old,
                   unified_displacements=len(ph.supercells_with_displacements),
                   count_definition='Prepared inputs at this geometry; excludes 0.no-move. Not a timing measurement.',
                   symprec_A=1e-5, displacement_A=DEFAULT_DISTANCE)
        source=gate_sources[name]
        if source.endswith('.tar.gz'):
            member='unified/0.no-move/zstar_insulation.json'
            with tarfile.open(ROOT/source) as archive:
                gate_bytes=archive.extractfile(member).read()
            source += ':'+member
        else:
            gate_bytes=(ROOT/source).read_bytes()
        gate=json.loads(gate_bytes)
        row.update(band_gap_eV=gate.get('gap_eV',gate.get('path_band_gap_eV')),
                   band_gap_source=source,
                   band_gap_record_sha256=hashlib.sha256(gate_bytes).hexdigest())
        assert row['band_gap_eV'] is not None
        rows.append(row)
    out=ROOT/'docs/research/reference_state_table_20260906.json'
    out.write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':
    main()
