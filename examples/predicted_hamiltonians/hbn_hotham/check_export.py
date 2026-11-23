"""Check the archived Hot-Ham exports against the disp-005 hBN control."""

from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.sparse import csr_matrix

from zstar.model_hamiltonian import read_abacus_real_csr, validate_hotham_export


def max_difference(left, right, size):
    zero = csr_matrix((size, size))
    return max(np.max(np.abs((left.get(r, zero) - right.get(r, zero)).data), initial=0.)
               for r in left.keys() | right.keys())


def sampled_gap(h, s, size):
    # Every translation has Rz=0, so all eight kz planes have the same bands.
    keys = sorted(h.keys() | s.keys())
    assert all(r[2] == 0 for r in keys)
    zero = csr_matrix((size, size))
    h_blocks, s_blocks = [np.array([m.get(r, zero).toarray() for r in keys])
                          for m in (h, s)]
    translations = np.asarray(keys)
    vbm, cbm = -np.inf, np.inf
    for i, j in np.ndindex(36, 36):
        phase = np.exp(2j * np.pi * (translations @ [i / 36, j / 36, 0]))
        hk = np.einsum("r,rij->ij", phase, h_blocks)
        sk = np.einsum("r,rij->ij", phase, s_blocks)
        occupied, empty = eigh(hk, sk, subset_by_index=[3, 4], eigvals_only=True)
        vbm, cbm = max(vbm, occupied), min(cbm, empty)
    return (cbm - vbm) * 13.605698


if __name__ == "__main__":
    common = Path("disp-005/common")
    sr = common / "data-SR-sparse_SPIN0.csr"
    validate_hotham_export("h_pred_0.csr", "olp.csr", sr)
    size, overlap = read_abacus_real_csr(sr)
    _, h = read_abacus_real_csr("h_pred_0.csr")
    _, control = read_abacus_real_csr(common / "data-HR-sparse_SPIN0.csr")
    _, h_ref = read_abacus_real_csr("h_ref_0.csr")
    _, olp = read_abacus_real_csr("olp.csr")
    print(f"Max exported S error     {max_difference(olp, overlap, size):.3e}")
    print(f"Max exported H_ref error {max_difference(h_ref, control, size):.3e} Ry")
    print(f"Predicted indirect gap   {sampled_gap(h, overlap, size):.6f} eV")
    print(f"ABACUS indirect gap      {sampled_gap(control, overlap, size):.6f} eV")
