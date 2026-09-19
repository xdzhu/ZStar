import hashlib
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = (
    Path(__file__).parents[1]
    / "examples"
    / "3D_Bulk"
    / "piezoelectric_v2_benchmarks"
    / "results"
    / "native_pbe_20260919"
)

CASES = {
    "AlN": {
        "sha256": "43aed4290101d427709eab942a84ce7ff975694ae7b66ae02a23f83d29ee69fd",
        "e": (-0.58149, 1.46140, -0.30953),
        "d33": 5.32368786794018,
    },
    "GaN": {
        "sha256": "482e8c34852922a43b11801eb21d59f29147292b2a0353884cd37cc6d5e4cef1",
        "e": (-0.26445, 0.42286, -0.14618),
        "d33": 1.5830536108147,
    },
    "ZnO": {
        "sha256": "3a4525ad7939836dc1c5af3d87b4f8ca2fd273b58c5447bb4cf32097d9db9095",
        "e": (-0.53688, 1.04205, -0.39928),
        "d33": 9.75007144198979,
    },
    "PTO": {
        "sha256": "15319a80f0d0c705e048c8a21760701aefebc91f51a8a5ce0c7116e73d5b5042",
        "e": (1.67007, 2.43952, 2.79597),
        "d33": 63.9946721603691,
    },
}


@pytest.mark.parametrize("material", CASES)
def test_native_pbe_archive_is_immutable_and_e_c_d_closed(material):
    path = ROOT / material / "vasp_native_response.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == CASES[material]["sha256"]
    record = json.loads(path.read_text(encoding="utf-8"))
    tensors = record["tensors"]
    e = np.asarray(tensors["piezoelectric_total_C_m2"], dtype=float)
    c = np.asarray(tensors["elastic_relaxed_GPa"], dtype=float)
    d = np.asarray(tensors["piezoelectric_d_pm_V"], dtype=float)
    e31, e33, e15 = CASES[material]["e"]
    np.testing.assert_allclose([e[2, 0], e[2, 2], e[0, 4]], [e31, e33, e15])
    assert d[2, 2] == pytest.approx(CASES[material]["d33"])
    np.testing.assert_allclose(d @ c / 1000.0, e, atol=1e-12)
    assert np.min(np.linalg.eigvalsh(0.5 * (c + c.T))) > 0.0
    assert tensors["piezoelectric_d_ec_closure_max_C_m2"] < 1e-12
    assert record["backend"] == "vasp"


@pytest.mark.parametrize("material", CASES)
def test_native_pbe_archive_records_hf_allocation(material):
    completed = json.loads((ROOT / material / "completed.json").read_text(encoding="utf-8"))
    assert completed["mpi"] == 32
    assert completed["omp"] == 1
    assert completed["core_hours"] > 0.0


def test_pto_independent_central_strain_is_closed_but_method_sensitive():
    path = ROOT / "PTO" / "independent_central_strain_005.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "820548aae82c454a88726988e69db3b714f0dcab483bd785529e4919a5bd3997"
    )
    central = json.loads(path.read_text(encoding="utf-8"))
    e_central = np.asarray(central["piezoelectric_proper_C_per_m2"], dtype=float)
    c_central = np.asarray(central["elastic_GPa"], dtype=float)
    d_central = np.asarray(central["piezoelectric_d_pm_per_V"], dtype=float)
    native = json.loads((ROOT / "PTO" / "vasp_native_response.json").read_text(encoding="utf-8"))["tensors"]
    e_native = np.asarray(native["piezoelectric_total_C_m2"], dtype=float)
    c_native = np.asarray(native["elastic_relaxed_GPa"], dtype=float)
    d_native = np.asarray(native["piezoelectric_d_pm_V"], dtype=float)
    np.testing.assert_allclose(d_central @ c_central / 1000.0, e_central, atol=1e-12)
    assert central["mechanical_stability"]["minimum_eigenvalue"] > 0.0
    assert central["stress_symmetrization"]["maximum_observed_antisymmetry_kbar"] <= 2.1e-7
    assert np.linalg.norm(c_central - c_native) / np.linalg.norm(c_native) < 0.004
    assert np.linalg.norm(e_central - e_native) / np.linalg.norm(e_native) > 0.07
    assert abs(d_central[2, 2] - d_native[2, 2]) / abs(d_native[2, 2]) > 0.18
