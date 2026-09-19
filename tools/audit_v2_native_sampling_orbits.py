"""Research-only input-span audit using existing v2 space-group representations."""
import argparse
import hashlib
import json
from pathlib import Path
import warnings

import numpy as np
from zstar.structure_io import read_structure
from zstar.v2.structure import (StructureSpec, analyze_space_group,
    displacement_representation, strain_representation, space_group_report_to_dict)


def orbit_span(vectors, representations, dimension, tolerance):
    vectors = np.asarray(vectors, dtype=float)
    if (vectors.ndim != 2 or vectors.shape[1] != dimension or not len(vectors)
            or not np.all(np.isfinite(vectors)) or tolerance <= 0):
        raise ValueError('Finite nonempty perturbation matrix and positive rank cutoff required')
    operations = tuple(np.asarray(op, dtype=float) for op in representations)
    if not operations or any(op.shape != (dimension, dimension) or not np.all(np.isfinite(op)) for op in operations):
        raise ValueError('Finite compatible symmetry representations required')
    expanded = np.concatenate([vectors@op.T for op in operations], axis=0)
    singular = np.linalg.svd(expanded, compute_uv=False)
    rank = int(np.count_nonzero(singular > tolerance))
    return {'raw_rank': int(np.linalg.matrix_rank(vectors, tol=tolerance)),
            'orbit_expanded_rank': rank, 'space_dimension': dimension,
            'expanded_row_count': len(expanded), 'singular_values': singular.tolist(),
            'absolute_rank_cutoff': tolerance, 'input_span_complete': rank == dimension}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('geometry-audit', 'poscar', 'outcar', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.geometry_audit.stat().st_size > 5_000_000:
        raise ValueError('Bounded input and new exclusive output required')
    source = json.loads(args.geometry_audit.read_text())
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if (source['poscar_sha256'] != digest(args.poscar) or
            source['outcar_sha256'] != digest(args.outcar)):
        raise ValueError('Actual geometry source hash mismatch')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        parent = read_structure(args.poscar)
        report = analyze_space_group(StructureSpec(parent.lattice_angstrom,
            parent.positions_fractional, parent.symbols))
    if report.status != 'stable' or report.symprec != .001 or report.diagnostics['rejected_operation_reasons']:
        raise ValueError('Trusted fixed-threshold atom mappings required')
    if list(parent.symbols) != source['species_in_input_order']:
        raise ValueError('Atom order mismatch')
    results = {}
    for kind, field, size, builder, cutoff in (
            ('atomic', 'nonaffine_displacement_angstrom', 3*len(parent.symbols), displacement_representation, 3e-5),
            ('strain', 'actual_engineering_strain', 6, strain_representation, 3e-6)):
        vectors = [np.asarray(row[field]).reshape(-1) for row in source['records'] if row['kind'] == kind]
        results[kind] = orbit_span(vectors, [builder(report, i) for i in range(report.operation_count)], size, cutoff)
        results[kind]['cutoff_unit'] = 'angstrom' if kind == 'atomic' else 'dimensionless engineering strain'
    result = {'schema': 'zstar.v2.native-sampling-orbit-span-research/1',
        'source_sha256': {str(p): digest(p) for p in (args.geometry_audit, args.poscar, args.outcar)},
        'algorithm_sha256': digest(Path(__file__)), 'symmetry': space_group_report_to_dict(report),
        'input_spans': results, 'input_span_complete': all(r['input_span_complete'] for r in results.values()),
        'response_reconstruction_verified': False, 'native_acceptance_changed': False,
        'warnings': [str(w.message) for w in caught], 'new_DFT_calculations': 0,
        'limitations': ['Rank cutoff follows OUTCAR text precision, not a new force or symmetry threshold.',
                       'Only perturbation input coverage is certified; native force/stress covariance and tensor accuracy are not certified.',
                       'Orbit images are symmetry-derived post-processing, not additional DFT tasks.']}
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'input_spans': results, 'input_span_complete': result['input_span_complete']}))


if __name__ == '__main__':
    main()
