"""Checks for scientific presentation and coordinate transformations."""

import json
from pathlib import Path
import unittest
import tempfile
import hashlib
import io
import tarfile

import numpy as np

from tools.shared_response.export_one_dimensional_bec import (
    read_case, cylindrical_tensors, sb_reference)
from tools.shared_response.report_one_dimensional_benchmark import timing
from tools.shared_response.verify_one_dimensional_example import difference, verify_archive, verify, verify_benchmark


class PublicationTest(unittest.TestCase):
    def test_completed_benchmarks_reproduce_costs_and_responses(self):
        root=Path(__file__).resolve().parents[2]/'examples/IR_Raman_Spectra'
        for name,speedup,interrupted,tolerance in [
                ('Nanowire_Sb2S3',2.199469275222015,0,.019),
                ('Nanotube_BN_9_0',2.1627016293898436,1,.515)]:
            report=verify_benchmark(root/name/'results')
            self.assertAlmostEqual(report['speedup'],speedup)
            self.assertEqual(report['unrecorded_interrupted_attempts'],interrupted)
            self.assertLess(report['independently_reconstructed_differences']['max_internal_frequency_difference_cm1'],tolerance)

    def test_archived_one_dimensional_spectra_follow_reconstructed_hessian(self):
        root=Path(__file__).resolve().parents[2]/'examples/IR_Raman_Spectra'
        for name in ('Nanotube_BN_9_0','Nanowire_Sb2S3'):
            report=verify(root/name)
            self.assertTrue(report['verified'])
            self.assertLess(report['maximum_errors']['dynamical_eigenvector_residual'],1e-9)

    def test_numerical_comparison_rejects_nonfinite_and_shape_mismatch(self):
        for value in ([np.nan], [[1]], [np.inf]):
            with self.assertRaisesRegex(ValueError,'shape/nonfinite'):
                difference(value,[1],1e-9,'test')
        with self.assertRaisesRegex(ValueError,'exceeds'):
            difference([2],[1],1e-9,'test')

    def test_archive_verification_is_read_only_and_rejects_corruption(self):
        data=b'native evidence'
        manifest={'files':[{'path':'native.log','size':len(data),
                            'sha256':hashlib.sha256(data).hexdigest()}]}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'evidence.tar.gz'
            for corrupt in (False,True):
                with tarfile.open(path,'w:gz') as archive:
                    for name,blob in [('evidence_manifest.json',json.dumps(manifest).encode()),
                                      ('native.log',b'corrupt' if corrupt else data)]:
                        info=tarfile.TarInfo(name)
                        info.size=len(blob)
                        archive.addfile(info,io.BytesIO(blob))
                before=path.read_bytes()
                if corrupt:
                    with self.assertRaisesRegex(ValueError,'digest mismatch'):
                        verify_archive(path)
                else:
                    self.assertEqual(verify_archive(path),1)
                self.assertEqual(path.read_bytes(),before)
                self.assertEqual(list(Path(tmp).iterdir()),[path])

    def test_timing_does_not_double_count_force_output_or_preparation(self):
        rows = [dict(kind=k,success=ok,wall_seconds=90,mpi=1,omp=40,
                     allocated_core_hours=1) for k,ok in
                [('ABACUS',True),('PYATB',True),('preparation',True),('ABACUS',False)]]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'times.jsonl'
            path.write_text('\n'.join(json.dumps(r) for r in rows))
            result=timing(path)
            self.assertEqual(result['successful_SCFs'],1)
            self.assertEqual(sum(result['costs'].values()),2)
            self.assertEqual(result['failed_core_hours'],1)
            rows[0]['allocated_core_hours']=2
            path.write_text('\n'.join(json.dumps(r) for r in rows))
            with self.assertRaisesRegex(ValueError,'disagree'):
                timing(path)

    def test_cylindrical_frame_preserves_trace_and_axial_component(self):
        s, p, z, _ = read_case('Nanotube_BN_9_0')
        local = cylindrical_tensors(p, s['cell_angstrom'], z)
        np.testing.assert_allclose(np.trace(local, axis1=1, axis2=2),
                                   np.trace(z, axis1=1, axis2=2), atol=1e-12)
        np.testing.assert_allclose(local[:,2,2], z[:,2,2])

    def test_cylindrical_frame_covariant_under_rotation_about_axis(self):
        s, p, z, _ = read_case('Nanotube_BN_9_0')
        a = .371
        r = np.array([[np.cos(a),-np.sin(a),0], [np.sin(a),np.cos(a),0], [0,0,1]])
        center = np.diag(s['cell_angstrom']) / 2
        rotated = (p-center) @ r.T + center
        np.testing.assert_allclose(cylindrical_tensors(rotated, s['cell_angstrom'], r @ z @ r.T),
                                  cylindrical_tensors(p, s['cell_angstrom'], z), atol=1e-12)

    def test_reference_mapping_unique_species_preserving(self):
        s, p, z, _ = read_case('Nanowire_Sb2S3')
        diagonal, audit = sb_reference(s, p)
        self.assertEqual(len(set(audit['reference_atom_1based'])), 10)
        self.assertLess(max(audit['matching_residual_A']), .064)
        # Preserve the source residual instead of silently neutralizing its data.
        np.testing.assert_allclose(diagonal.sum(axis=0), [-4e-8, 1.4e-7, 1.18e-6], atol=2e-14)
        self.assertAlmostEqual(diagonal[6,2], 4.34097421)

    def test_unified_archives_contain_joint_observations(self):
        root = Path(__file__).resolve().parents[2] / 'examples/IR_Raman_Spectra'
        for name, count in [('Nanotube_BN_9_0',56), ('Nanowire_Sb2S3',20)]:
            directory = root/name/'results'
            manifest = json.loads((directory/'shared_response.json').read_text())
            fit = json.loads((directory/'response_fit.json').read_text())
            self.assertEqual(manifest['dimension'],1)
            self.assertEqual(manifest['displacement_scheme'],'phonopy')
            self.assertEqual(len(manifest['stages']),count)
            self.assertEqual(len(fit['observations']),count)
            for observation in fit['observations']:
                self.assertIn('dipole_change_e_A',observation)
                self.assertIn('forces_eV_A',observation)


if __name__ == '__main__':
    unittest.main()
