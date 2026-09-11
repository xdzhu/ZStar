"""Research-only ZStar v2 API, isolated from the stable v1 surface."""

from .algebra import internal_strain_response, relaxed_elastic, relaxed_piezoelectric
from .ensemble import PerturbationStage, ResponseEnsemble, V2StateStore, plan_central_stages
from .fit import LinearFitResult, central_difference, fit_linear_response
from .mechanical import (
    ENGINEERING_VOIGT,
    mechanical_stability,
    strain_tensor_to_voigt,
    stress_tensor_to_voigt,
    voigt_to_strain_tensor,
    voigt_to_stress_tensor,
)
from .model import (
    V2_SCHEMA_NAME,
    V2_SCHEMA_VERSION,
    BoundaryConditions,
    ResponseDocument,
    TensorQuantity,
)
from .symmetry import (
    IntertwinerBasis,
    intertwiner_basis,
    intertwiner_constraint_matrix,
    intertwining_residual,
    project_intertwiner,
)
from .structure import (
    SpaceGroupOperation,
    SpaceGroupReport,
    StructureSpec,
    allowed_response_basis,
    analyze_space_group,
    displacement_representation,
    polarization_representation,
    strain_representation,
)
from .units import EPSILON_0, ELEMENTARY_CHARGE, UnitConversionError, convert_dielectric, convert_values

__all__ = [
    "BoundaryConditions",
    "ENGINEERING_VOIGT",
    "EPSILON_0",
    "ELEMENTARY_CHARGE",
    "IntertwinerBasis",
    "LinearFitResult",
    "PerturbationStage",
    "ResponseDocument",
    "ResponseEnsemble",
    "SpaceGroupOperation",
    "SpaceGroupReport",
    "StructureSpec",
    "TensorQuantity",
    "UnitConversionError",
    "V2StateStore",
    "V2_SCHEMA_NAME",
    "V2_SCHEMA_VERSION",
    "central_difference",
    "allowed_response_basis",
    "analyze_space_group",
    "convert_dielectric",
    "convert_values",
    "fit_linear_response",
    "intertwiner_basis",
    "intertwiner_constraint_matrix",
    "intertwining_residual",
    "internal_strain_response",
    "mechanical_stability",
    "plan_central_stages",
    "displacement_representation",
    "polarization_representation",
    "project_intertwiner",
    "relaxed_elastic",
    "relaxed_piezoelectric",
    "strain_tensor_to_voigt",
    "stress_tensor_to_voigt",
    "strain_representation",
    "voigt_to_strain_tensor",
    "voigt_to_stress_tensor",
]
