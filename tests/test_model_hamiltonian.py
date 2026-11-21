"""Model conversion regression tests for signed basis and translation errors."""

import json

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from zstar.model_hamiltonian import (
    EV_PER_RY,
    convert_deeph,
    convert_hamgnn,
    read_abacus_real_csr,
    write_abacus_real_csr,
)


def test_deeph_inverts_offdiagonal_p_orbitals_and_checks_overlap(tmp_path):
    h5py = pytest.importorskip("h5py")
    origin = (0, 0, 0)
    overlap = np.eye(3)
    overlap[0, 1] = overlap[1, 0] = 0.02
    hamiltonian = np.array([[0.5, 0.1, 0.25], [0.1, 2.0, -0.3], [0.25, -0.3, 4.0]])
    forward = np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]])
    reference = write_abacus_real_csr(tmp_path/"S.csr", {origin: csr_matrix(overlap)}, 3)
    orbitals = tmp_path/"orbital_types.dat"
    orbitals.write_text("1\n")
    key = json.dumps([0, 0, 0, 1, 1])
    with h5py.File(tmp_path/"overlaps.h5", "w") as f:
        f[key] = forward @ overlap @ forward.T
    with h5py.File(tmp_path/"hamiltonians_pred.h5", "w") as f:
        f[key] = EV_PER_RY * forward @ hamiltonian @ forward.T
    output = convert_deeph(tmp_path/"hamiltonians_pred.h5", orbitals, tmp_path/"overlaps.h5",
                          reference, tmp_path/"H.csr")
    _, matrices = read_abacus_real_csr(output)
    np.testing.assert_allclose(matrices[origin].toarray(), hamiltonian)
    with h5py.File(tmp_path/"overlaps.h5", "r+") as f:
        f[key][0, 2] = 0.5
    with pytest.raises(ValueError, match="differs from ABACUS"):
        convert_deeph(tmp_path/"hamiltonians_pred.h5", orbitals, tmp_path/"overlaps.h5",
                      reference, tmp_path/"wrong.csr")
    assert not (tmp_path/"wrong.csr").exists()


def test_hamgnn_uses_shifts_masks_and_hartree(tmp_path):
    onsite = np.array([[[1., 0], [0, 0]], [[0., 0], [0, 1.]]])
    offsite = np.array([[[0., .25], [0., 0.]], [[0., 0.], [.25, 0.]]])
    np.savez(tmp_path/"graph.npz", orbital_mask=np.eye(2, dtype=bool),
             edge_index=[[0, 1], [1, 0]], cell_shift=[[0, 0, 1], [0, 0, -1]],
             Son=onsite, Soff=offsite)
    np.save(tmp_path/"prediction.npy", np.concatenate((onsite, offsite)))
    reference = write_abacus_real_csr(
        tmp_path/"S.csr",
        {(0, 0, 0): csr_matrix(np.eye(2)), (0, 0, 1): csr_matrix([[0, .25], [0, 0]]),
         (0, 0, -1): csr_matrix([[0, 0], [.25, 0]])},
        2,
    )
    result = convert_hamgnn(tmp_path/"prediction.npy", tmp_path/"graph.npz", reference, tmp_path/"H.csr")
    _, h = read_abacus_real_csr(result)
    assert h[(0, 0, 1)][0, 1] == pytest.approx(0.5)
    assert h[(0, 0, -1)][1, 0] == pytest.approx(0.5)
