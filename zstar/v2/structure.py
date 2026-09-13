"""Structure-level space-group analysis for the ZStar v2 symmetry engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from ..dimensions import DimensionSpec
from .mechanical import (
    strain_tensor_to_voigt,
    stress_representation,
    voigt_to_strain_tensor,
)
from .symmetry import intertwiner_basis

try:
    import spglib
except Exception:  # pragma: no cover - dependency is declared by the package
    spglib = None


def _array(value: object, shape: tuple[int, ...], name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape:
        raise ValueError(f"{name} must have shape {shape}; got {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values")
    return array


@dataclass(frozen=True)
class StructureSpec:
    """Minimal calculator-neutral periodic structure description."""

    lattice: np.ndarray
    fractional_positions: np.ndarray
    symbols: tuple[str, ...]
    dimensionality: DimensionSpec = DimensionSpec(3)

    def __post_init__(self) -> None:
        lattice = _array(self.lattice, (3, 3), "lattice")
        positions = np.asarray(self.fractional_positions, dtype=float)
        if positions.ndim != 2 or positions.shape[1] != 3 or positions.shape[0] == 0:
            raise ValueError(f"fractional_positions must have shape (natom, 3); got {positions.shape}")
        if not np.all(np.isfinite(positions)):
            raise ValueError("fractional_positions contains non-finite values")
        symbols = tuple(str(symbol) for symbol in self.symbols)
        if len(symbols) != positions.shape[0] or any(not symbol.strip() for symbol in symbols):
            raise ValueError("symbols must contain one non-empty label per atom")
        if abs(float(np.linalg.det(lattice))) <= 1.0e-14:
            raise ValueError("lattice must be non-singular")
        object.__setattr__(self, "lattice", lattice)
        object.__setattr__(self, "fractional_positions", positions % 1.0)
        object.__setattr__(self, "symbols", symbols)

    @property
    def atom_count(self) -> int:
        return len(self.symbols)

    def spglib_cell(self) -> tuple[np.ndarray, np.ndarray, list[int]]:
        type_ids: dict[str, int] = {}
        numbers: list[int] = []
        for symbol in self.symbols:
            type_ids.setdefault(symbol, len(type_ids) + 1)
            numbers.append(type_ids[symbol])
        return self.lattice, self.fractional_positions, numbers


@dataclass(frozen=True)
class SpaceGroupOperation:
    rotation_fractional: np.ndarray
    translation_fractional: np.ndarray
    rotation_cartesian: np.ndarray
    permutation: tuple[int, ...]


@dataclass(frozen=True)
class SpaceGroupReport:
    status: str
    symprec: float
    space_group: str | None
    hall_number: int | None
    equivalent_atoms: tuple[int, ...]
    representatives: tuple[int, ...]
    operations: tuple[SpaceGroupOperation, ...]
    diagnostics: dict[str, object]

    @property
    def atom_count(self) -> int:
        return len(self.equivalent_atoms)

    @property
    def operation_count(self) -> int:
        return len(self.operations)


@dataclass(frozen=True)
class SymmetryInputPlan:
    """Minimal canonical input directions that identify allowed responses.

    ``vectors`` contains rows in the input representation's canonical basis.
    It is a task-selection plan, not a claim that the corresponding response
    has been calculated; rank and residual checks still belong to fitting.
    """

    input_kind: str
    output_kinds: tuple[str, ...]
    vectors: np.ndarray
    selected_indices: tuple[int, ...]
    allowed_ranks: dict[str, int]
    identified_rank: int
    tolerance: float

    @property
    def complete(self) -> bool:
        return self.identified_rank == sum(self.allowed_ranks.values())

    def to_dict(self) -> dict[str, object]:
        return {
            "input_kind": self.input_kind,
            "output_kinds": list(self.output_kinds),
            "vectors": np.asarray(self.vectors, dtype=float).tolist(),
            "selected_indices": list(self.selected_indices),
            "allowed_ranks": dict(self.allowed_ranks),
            "identified_rank": int(self.identified_rank),
            "complete": self.complete,
            "tolerance": float(self.tolerance),
        }


def _dataset_value(dataset: object, name: str):
    return getattr(dataset, name) if hasattr(dataset, name) else dataset[name]


def _wrapped_distance(first: np.ndarray, second: np.ndarray, lattice: np.ndarray) -> float:
    delta = (first - second + 0.5) % 1.0 - 0.5
    return float(np.linalg.norm(delta @ lattice))


def _operation_permutation(
    structure: StructureSpec,
    rotation: np.ndarray,
    translation: np.ndarray,
    tolerance: float,
) -> tuple[int, ...] | None:
    transformed = (structure.fractional_positions @ rotation.T + translation) % 1.0
    candidate_lists: list[list[tuple[float, int]]] = []
    for index, position in enumerate(transformed):
        candidates = sorted(
            (
                _wrapped_distance(position, structure.fractional_positions[target], structure.lattice),
                target,
            )
            for target, symbol in enumerate(structure.symbols)
            if symbol == structure.symbols[index]
        )
        if not candidates or candidates[0][0] > tolerance:
            return None
        candidate_lists.append([item for item in candidates if item[0] <= tolerance])

    # Resolve the species-preserving assignment as a bipartite matching rather
    # than a greedy nearest-neighbour walk.  Near-degenerate Wyckoff sites can
    # make a greedy choice consume the only target of a later atom even though
    # a valid bijection exists.
    source_order = sorted(range(len(candidate_lists)), key=lambda item: (len(candidate_lists[item]), item))
    target_owner: dict[int, int] = {}

    def assign(source: int, visited: set[int]) -> bool:
        for _distance, target in candidate_lists[source]:
            if target in visited:
                continue
            visited.add(target)
            owner = target_owner.get(target)
            if owner is None or assign(owner, visited):
                target_owner[target] = source
                return True
        return False

    for source in source_order:
        if not assign(source, set()):
            return None
    permutation = [0] * len(candidate_lists)
    for target, source in target_owner.items():
        permutation[source] = target
    return tuple(permutation)


def _boundary_compatible(rotation: np.ndarray, dimensionality: DimensionSpec, tolerance: float = 1.0e-7) -> bool:
    periodic = {"xyz".index(axis) for axis in dimensionality.periodic_axes}
    open_axes = set(range(3)) - periodic
    if not open_axes or not periodic:
        return True
    for periodic_axis in periodic:
        for open_axis in open_axes:
            if abs(float(rotation[periodic_axis, open_axis])) > tolerance:
                return False
            if abs(float(rotation[open_axis, periodic_axis])) > tolerance:
                return False
    return True


def analyze_space_group(
    structure: StructureSpec,
    *,
    symprec_grid: Iterable[float] = (1.0e-5, 1.0e-4, 1.0e-3),
) -> SpaceGroupReport:
    """Identify a stable space group and validate it against dimensionality."""

    if structure.dimensionality.value == 0:
        identity = SpaceGroupOperation(
            rotation_fractional=np.eye(3),
            translation_fractional=np.zeros(3),
            rotation_cartesian=np.eye(3),
            permutation=tuple(range(structure.atom_count)),
        )
        return SpaceGroupReport(
            status="molecular-no-periodic-symmetry",
            symprec=0.0,
            space_group=None,
            hall_number=None,
            equivalent_atoms=tuple(range(structure.atom_count)),
            representatives=tuple(range(structure.atom_count)),
            operations=(identity,),
            diagnostics={"periodic_reduction": False},
        )
    if spglib is None:
        raise RuntimeError("spglib is required for periodic v2 symmetry analysis")
    candidates = []
    for value in symprec_grid:
        tolerance = float(value)
        if not np.isfinite(tolerance) or tolerance <= 0.0:
            raise ValueError("symprec_grid values must be finite and positive")
        dataset = spglib.get_symmetry_dataset(structure.spglib_cell(), symprec=tolerance)
        if dataset is None:
            continue
        rotations = np.asarray(_dataset_value(dataset, "rotations"), dtype=int)
        translations = np.asarray(_dataset_value(dataset, "translations"), dtype=float)
        operations: list[SpaceGroupOperation] = []
        rejected_operations: list[str] = []
        cartesian_basis = structure.lattice.T
        inverse_basis = np.linalg.inv(cartesian_basis)
        for rotation, translation in zip(rotations, translations):
            permutation = _operation_permutation(structure, rotation, translation, max(tolerance * 2.0, 1.0e-7))
            if permutation is None:
                rejected_operations.append("atom_mapping")
                continue
            rotation_cartesian = cartesian_basis @ rotation @ inverse_basis
            orthogonality_error = float(
                np.max(np.abs(rotation_cartesian.T @ rotation_cartesian - np.eye(3)))
            )
            determinant_error = abs(abs(float(np.linalg.det(rotation_cartesian))) - 1.0)
            operation_tolerance = max(tolerance * 10.0, 1.0e-7)
            if orthogonality_error > operation_tolerance or determinant_error > operation_tolerance:
                rejected_operations.append("non_orthogonal_rotation")
                continue
            if not _boundary_compatible(rotation_cartesian, structure.dimensionality):
                rejected_operations.append("boundary_mixing")
                continue
            operations.append(SpaceGroupOperation(rotation, translation, rotation_cartesian, permutation))
        equivalent = tuple(int(value) for value in _dataset_value(dataset, "equivalent_atoms"))
        candidates.append((
            tolerance,
            str(_dataset_value(dataset, "international")),
            int(_dataset_value(dataset, "hall_number")),
            equivalent,
            tuple(operations),
            tuple(rejected_operations),
        ))
    if not candidates:
        return SpaceGroupReport(
            status="symmetry_untrusted",
            symprec=0.0,
            space_group=None,
            hall_number=None,
            equivalent_atoms=tuple(range(structure.atom_count)),
            representatives=tuple(range(structure.atom_count)),
            operations=(),
            diagnostics={"reason": "spglib returned no stable dataset"},
        )
    # Prefer the tightest tolerance that agrees with at least one other candidate.
    signatures = {(item[1], item[2], item[3], len(item[4])) for item in candidates}
    best = min(candidates, key=lambda item: item[0])
    best_signature = (best[1], best[2], best[3], len(best[4]))
    stable = len(signatures) == 1 or any(
        (item[1], item[2], item[3], len(item[4])) == best_signature
        for item in candidates
        if item is not best
    )
    equivalent = best[3]
    representatives = tuple(index for index, representative in enumerate(equivalent) if representative == index)
    status = "stable" if stable and best[4] else "symmetry_untrusted"
    return SpaceGroupReport(
        status=status,
        symprec=best[0],
        space_group=best[1],
        hall_number=best[2],
        equivalent_atoms=equivalent,
        representatives=representatives,
        operations=best[4],
        diagnostics={
            "candidate_count": len(candidates),
                "candidate_signatures": [
                    {"symprec": item[0], "space_group": item[1], "hall_number": item[2], "operation_count": len(item[4])}
                for item in candidates
            ],
            "boundary_compatible_operations": len(best[4]),
            "rejected_operation_reasons": list(best[5]),
        },
    )


def displacement_representation(report: SpaceGroupReport, operation_index: int) -> np.ndarray:
    """Build the atom-Cartesian displacement representation for one operation."""

    operation = report.operations[int(operation_index)]
    size = 3 * report.atom_count
    matrix = np.zeros((size, size), dtype=float)
    for source, target in enumerate(operation.permutation):
        matrix[3 * target : 3 * target + 3, 3 * source : 3 * source + 3] = operation.rotation_cartesian
    return matrix


def polarization_representation(report: SpaceGroupReport, operation_index: int) -> np.ndarray:
    return np.asarray(report.operations[int(operation_index)].rotation_cartesian, dtype=float)


def strain_representation(report: SpaceGroupReport, operation_index: int) -> np.ndarray:
    """Build the 6x6 engineering-Voigt representation from Cartesian rotation."""

    rotation = report.operations[int(operation_index)].rotation_cartesian
    matrix = np.zeros((6, 6), dtype=float)
    for column in range(6):
        transformed = rotation @ voigt_to_strain_tensor(np.eye(6)[column]) @ rotation.T
        matrix[:, column] = strain_tensor_to_voigt(transformed)
    return matrix


def allowed_response_basis(
    report: SpaceGroupReport,
    *,
    input_kind: str,
    output_kind: str,
):
    """Return an intertwiner basis for displacement/polarization/strain axes."""

    if not report.operations:
        raise ValueError("cannot build a symmetry basis without operations")
    builders = {
        # Forces transform as Cartesian covectors under the same orthogonal
        # rotations as displacements; retaining the alias lets the unified
        # strain plan constrain force and internal-displacement outputs with
        # one representation definition.
        "displacement": lambda index: displacement_representation(report, index),
        "force": lambda index: displacement_representation(report, index),
        "polarization": lambda index: polarization_representation(report, index),
        "strain": lambda index: strain_representation(report, index),
        # Stress uses undoubled tensorial shear components, unlike engineering
        # strain.  Do not reuse strain_representation here: that would impose
        # the wrong intertwining metric on stress <- strain fits.
        "stress": lambda index: stress_representation(report.operations[int(index)].rotation_cartesian),
    }
    if input_kind not in builders or output_kind not in builders:
        raise ValueError("input_kind and output_kind must be displacement, polarization or strain")
    return intertwiner_basis(
        tuple(builders[input_kind](index) for index in range(report.operation_count)),
        tuple(builders[output_kind](index) for index in range(report.operation_count)),
    )


def symmetry_adapted_input_plan(
    report: SpaceGroupReport,
    *,
    input_kind: str,
    output_kinds: str | Iterable[str] = "polarization",
    tolerance: float = 1.0e-10,
) -> SymmetryInputPlan:
    """Select canonical perturbations sufficient to identify allowed responses.

    For each candidate canonical input direction, the function evaluates all
    matrices in the corresponding intertwiner basis and greedily retains a
    direction only when it increases the combined coefficient rank across the
    requested output kinds.  This reduces first-principles geometries while
    keeping the fit auditable: the returned plan carries the allowed rank and
    must still be checked against the rank of measured observations.

    The method is representation-based and does not assume a crystallographic
    point group.  For a unified strain ensemble, pass
    ``input_kind="strain"`` and ``output_kinds=("polarization", "strain")``;
    add ``"displacement"`` when relaxed-ion internal coordinates are needed.
    """

    if not report.operations:
        raise ValueError("cannot build a symmetry-adapted input plan without operations")
    if not np.isfinite(float(tolerance)) or float(tolerance) <= 0.0:
        raise ValueError("tolerance must be finite and positive")
    input_name = str(input_kind).strip().lower()
    if not input_name:
        raise ValueError("input_kind must be non-empty")
    if isinstance(output_kinds, str):
        outputs = (output_kinds,)
    else:
        outputs = tuple(str(kind) for kind in output_kinds)
    outputs = tuple(str(kind).strip().lower() for kind in outputs)
    if not outputs or any(not kind for kind in outputs):
        raise ValueError("output_kinds must contain at least one non-empty kind")
    if len(set(outputs)) != len(outputs):
        raise ValueError("output_kinds must not contain duplicates")

    bases = {
        kind: allowed_response_basis(report, input_kind=input_name, output_kind=kind)
        for kind in outputs
    }
    input_dimension = next(iter(bases.values())).input_dimension
    if any(basis.input_dimension != input_dimension for basis in bases.values()):
        raise ValueError("response bases disagree on input dimension")
    allowed_ranks = {kind: basis.allowed_rank for kind, basis in bases.items()}
    total_rank = sum(allowed_ranks.values())
    if total_rank == 0:
        return SymmetryInputPlan(
            input_kind=input_name,
            output_kinds=outputs,
            vectors=np.zeros((0, input_dimension), dtype=float),
            selected_indices=(),
            allowed_ranks=allowed_ranks,
            identified_rank=0,
            tolerance=float(tolerance),
        )

    coefficient_matrices: dict[str, list[np.ndarray]] = {}
    for kind, basis in bases.items():
        coefficient_matrices[kind] = [
            basis.matrix_from_coefficients(np.eye(basis.allowed_rank, dtype=float)[index])
            for index in range(basis.allowed_rank)
        ]

    def feature(direction: np.ndarray) -> np.ndarray:
        row_count = sum(bases[kind].output_dimension for kind in outputs)
        combined = np.zeros((row_count, total_rank), dtype=float)
        row_offset = 0
        column_offset = 0
        for kind in outputs:
            # Rows are output components and columns are unknown symmetry
            # coefficients.  This orientation is essential for rank tests.
            matrices = coefficient_matrices[kind]
            if matrices:
                block = np.stack(
                    [matrix @ direction for matrix in matrices],
                    axis=1,
                )
            else:
                # A response can be symmetry-forbidden (allowed rank zero)
                # while another output in the same unified plan remains
                # active. Keep an explicit zero-column block so the combined
                # rank calculation still includes the latter output.
                block = np.zeros((bases[kind].output_dimension, 0), dtype=float)
            rows = slice(row_offset, row_offset + block.shape[0])
            columns = slice(column_offset, column_offset + block.shape[1])
            combined[rows, columns] = block
            row_offset += block.shape[0]
            column_offset += block.shape[1]
        return combined

    selected: list[int] = []
    selected_features = np.zeros((0, total_rank), dtype=float)
    identified_rank = 0
    for index in range(input_dimension):
        direction = np.eye(input_dimension, dtype=float)[index]
        candidate = np.vstack([selected_features, feature(direction)])
        candidate_rank = int(np.linalg.matrix_rank(candidate, tol=float(tolerance)))
        if candidate_rank > identified_rank:
            selected.append(index)
            selected_features = candidate
            identified_rank = candidate_rank
        if identified_rank == total_rank:
            break
    vectors = np.eye(input_dimension, dtype=float)[selected] if selected else np.zeros((0, input_dimension))
    return SymmetryInputPlan(
        input_kind=input_name,
        output_kinds=outputs,
        vectors=vectors,
        selected_indices=tuple(selected),
        allowed_ranks=allowed_ranks,
        identified_rank=identified_rank,
        tolerance=float(tolerance),
    )
