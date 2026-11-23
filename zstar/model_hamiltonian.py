"""Convert model predictions to the ABACUS real-space CSR consumed by PYATB."""

from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from scipy.linalg import block_diag
from scipy.sparse import coo_matrix, csr_matrix


EV_PER_RY = 13.605698
_ZERO = (0, 0, 0)


def read_abacus_real_csr(path, *, kind=None):
    """Read ABACUS legacy text CSR blocks without densifying the basis."""
    with Path(path).open(encoding="ascii") as handle:
        header = handle.readline()
        if header.startswith("STEP:"):
            header = handle.readline()
        count_line = handle.readline()
        if kind and (not header.startswith(f"Matrix Dimension of {kind}(R): ")
                     or not count_line.startswith(f"Matrix number of {kind}(R): ")):
            raise ValueError(f"Expected a Hot-Ham {kind}(R) export in {path}")
        if not header.startswith("Matrix Dimension") or not count_line.startswith("Matrix number"):
            raise ValueError(f"Expected ABACUS text CSR header in {path}")
        size, count = int(header.split()[-1]), int(count_line.split()[-1])
        if size <= 0 or count <= 0:
            raise ValueError("ABACUS matrix size and number of lattice blocks must be positive")
        blocks = {}
        for _ in range(count):
            x, y, z, nnz = map(int, handle.readline().split())
            key = (x, y, z)
            if key in blocks or nnz < 0:
                raise ValueError("Duplicate translation or invalid nonzero count in ABACUS CSR")
            if nnz == 0:
                blocks[key] = csr_matrix((size, size))
                continue
            try:
                values = np.array(handle.readline().split(), dtype=float)
            except ValueError as exc:
                raise ValueError(f"Expected real CSR values at translation {key} in {path}") from exc
            columns = np.array(handle.readline().split(), dtype=int)
            rows = np.array(handle.readline().split(), dtype=int)
            if (len(values) != nnz or len(columns) != nnz or len(rows) != size + 1
                    or not np.isfinite(values).all() or rows[0] != 0 or rows[-1] != nnz
                    or np.any(np.diff(rows) < 0) or np.any(columns < 0) or np.any(columns >= size)):
                raise ValueError("Invalid ABACUS CSR data")
            matrix = csr_matrix((values, columns, rows), shape=(size, size))
            if not matrix.has_canonical_format:
                raise ValueError("ABACUS CSR column indices must be sorted and unique")
            blocks[key] = matrix
        if handle.read().strip():
            raise ValueError("Unexpected data after ABACUS CSR blocks")
    return size, blocks


def write_abacus_real_csr(path, blocks, size):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"STEP: 0\nMatrix Dimension of H(R): {size}\nMatrix number of H(R): {len(blocks)}\n")
        for key, matrix in sorted(blocks.items()):
            matrix.eliminate_zeros()
            handle.write("{} {} {} {}\n".format(*key, matrix.nnz))
            if matrix.nnz:
                handle.write(" ".join(f"{v:.16e}" for v in matrix.data) + "\n")
                handle.write(" ".join(map(str, matrix.indices)) + "\n")
                handle.write(" ".join(map(str, matrix.indptr)) + "\n")
    return path


def _basis_inverse(shells):
    # Inverse of the real ABACUS -> DeepH-pack convention in
    # deeph/preprocess/abacus_get_data.py, using signed permutations.
    perm = ([0], [1, 2, 0], [0, 3, 4, 1, 2], list(range(7)))
    negative_rows = ([], [0, 1], [3, 4], [1, 2, 5, 6])
    blocks = []
    for l in shells:
        if not 0 <= l <= 3:
            raise ValueError("DeepH ABACUS conversion supports s through f shells")
        part = np.eye(2*l + 1)[perm[l]]
        part[negative_rows[l], :] *= -1
        blocks.append(part.T)
    if not blocks:
        raise ValueError("Each atom must have at least one shell")
    return block_diag(*blocks)


def _assembled(blocks, counts):
    size = sum(counts)
    offsets = np.r_[0, np.cumsum(counts)]
    values = defaultdict(list)
    for (shift, i, j), matrix in blocks:
        matrix = np.asarray(matrix)
        if (not 0 <= i < len(counts) or not 0 <= j < len(counts)
                or matrix.shape != (counts[i], counts[j]) or np.iscomplexobj(matrix)
                or not np.isfinite(matrix).all()):
            raise ValueError("Invalid atom-pair block or unsupported complex Hamiltonian")
        row, col = np.nonzero(matrix)
        values[shift].append((matrix[row, col], row + offsets[i], col + offsets[j]))
    if not values:
        raise ValueError("No atom-pair blocks found")
    output = {}
    for shift, chunks in values.items():
        data, row, col = [np.concatenate(parts) for parts in zip(*chunks)]
        output[shift] = coo_matrix((data, (row, col)), shape=(size, size)).tocsr()
    return output


def _read_deeph_blocks(path, inverse):
    try:
        import h5py
    except ImportError as exc:
        raise ImportError("Reading DeepH predictions requires h5py") from exc
    with h5py.File(path, "r") as data:
        seen = set()
        for key in data:
            if not isinstance(data.get(key, getlink=True), h5py.HardLink):
                raise ValueError("DeepH matrix must store local datasets")
            indices = json.loads(key)
            if not isinstance(indices, list) or len(indices) != 5 or not all(type(v) is int for v in indices):
                raise ValueError(f"Invalid DeepH atom-pair key: {key}")
            shift, i, j = tuple(indices[:3]), indices[3]-1, indices[4]-1
            if not 0 <= i < len(inverse) or not 0 <= j < len(inverse) or (shift, i, j) in seen:
                raise ValueError("DeepH atom index is invalid or duplicated")
            seen.add((shift, i, j))
            mat = np.asarray(data[key])
            if mat.shape != (len(inverse[i]), len(inverse[j])) or np.iscomplexobj(mat):
                raise ValueError("DeepH dataset does not match the real spin-degenerate basis")
            yield (shift, i, j), inverse[i] @ mat @ inverse[j].T


def _verify_overlap(actual, reference_path, size, tol):
    expected_size, expected = read_abacus_real_csr(reference_path)
    if expected_size != size or _ZERO not in actual or _ZERO not in expected:
        raise ValueError("Model overlap does not match the ABACUS basis")
    zero = csr_matrix((size, size))
    for shift in actual.keys() | expected.keys():
        residual = actual.get(shift, zero) - expected.get(shift, zero)
        if np.max(np.abs(residual.data), initial=0.0) > tol:
            raise ValueError(f"Model overlap differs from ABACUS at translation {shift}")


def _symmetrize_hamiltonian(matrices):
    # Match the model band calculations, which Hermitianize H(k).
    # Take the equivalent average in real space before PYATB forms H(k).
    zero = csr_matrix(next(iter(matrices.values())).shape)
    translations = matrices.keys() | {tuple(-x for x in shift) for shift in matrices}
    return {
        shift: (matrices.get(shift, zero) +
                matrices.get(tuple(-x for x in shift), zero).T) * .5
        for shift in translations
    }


def validate_hotham_export(prediction, model_overlap, reference_overlap):
    """Check native spin-1 CSR files from a single ABACUS Hot-Ham inference."""
    size, overlap = read_abacus_real_csr(model_overlap, kind="S")
    _verify_overlap(overlap, reference_overlap, size, 2e-6)
    h_size, h = read_abacus_real_csr(prediction, kind="H")
    if h_size != size or _ZERO not in h:
        raise ValueError("Hot-Ham H and S must share a basis and include the home cell")
    zero = csr_matrix((size, size))
    for shift, matrix in h.items():
        reverse = tuple(-i for i in shift)
        residual = matrix - h.get(reverse, zero).T
        if np.max(np.abs(residual.data), initial=0.) > 2e-6:
            raise ValueError(f"Hot-Ham H(R) differs from H(-R)^T at {shift}")


def convert_deeph(prediction, orbital_types, model_overlap, reference_overlap, output):
    """Convert a spin-degenerate DeepH-pack prediction in eV to ABACUS Ry."""
    rows = Path(orbital_types).read_text(encoding="ascii").splitlines()
    inverse = [_basis_inverse([int(v) for v in row.split()]) for row in rows if row.strip()]
    counts = [len(block) for block in inverse]
    size = sum(counts)
    overlap = _assembled(_read_deeph_blocks(model_overlap, inverse), counts)
    _verify_overlap(overlap, reference_overlap, size, 2e-6)
    hamiltonian = _assembled(
        ((key, value / EV_PER_RY) for key, value in _read_deeph_blocks(prediction, inverse)), counts
    )
    return write_abacus_real_csr(output, _symmetrize_hamiltonian(hamiltonian), size)


def convert_hamgnn(prediction, graph, reference_overlap, output):
    """Convert a real, single-structure HamGNN prediction using numeric graph arrays."""
    with np.load(graph, allow_pickle=False) as data:
        masks = data["orbital_mask"]
        edges, shifts = data["edge_index"], data["cell_shift"]
        onsite, offsite = data["Son"], data["Soff"]
    if masks.ndim != 2 or masks.dtype != np.bool_ or not np.all(masks.any(axis=1)):
        raise ValueError("Each HamGNN atom must declare a boolean orbital mask")
    nat, nao = masks.shape
    if (edges.ndim != 2 or edges.shape[0] != 2 or not np.issubdtype(edges.dtype, np.integer)
            or np.any(edges < 0) or np.any(edges >= nat)):
        raise ValueError("Invalid HamGNN edge_index")
    nedges = edges.shape[1]
    if shifts.shape != (nedges, 3) or not np.issubdtype(shifts.dtype, np.integer):
        raise ValueError("HamGNN cell shifts must be integer triples")
    if onsite.shape != (nat, nao, nao) or offsite.shape != (nedges, nao, nao):
        raise ValueError("Split HamGNN overlaps must use the same max orbital count")
    raw = np.load(prediction, allow_pickle=False, mmap_mode="r")
    if raw.shape not in {(nat + nedges, nao * nao), (nat + nedges, nao, nao)}:
        raise ValueError("Prediction must contain one onsite block per atom and one per edge")
    raw = raw.reshape(nat + nedges, nao, nao)
    keys = [(_ZERO, i, i) for i in range(nat)] + [
        (tuple(shift), int(i), int(j)) for shift, (i, j) in zip(shifts, edges.T)
    ]
    if len(set(keys)) != len(keys):
        raise ValueError("HamGNN structure contains duplicate onsite/edge blocks")
    counts = [int(mask.sum()) for mask in masks]

    def matrices(blocks):
        return _assembled(
            ((key, block[np.ix_(masks[key[1]], masks[key[2]])])
              for key, block in zip(keys, blocks)), counts
        )

    overlap = matrices(np.concatenate((onsite, offsite), axis=0))
    _verify_overlap(overlap, reference_overlap, sum(counts), 2e-6)
    # The official ABACUS graph outputs use Hartree for H. CSR stores Ry.
    return write_abacus_real_csr(output, _symmetrize_hamiltonian(matrices(raw * 2.0)), sum(counts))
