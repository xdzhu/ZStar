"""Thermodynamic conversions between the four piezoelectric forms.

The routines in this module are calculator-neutral and operate on the SI
strain-charge convention documented in ``docs/v2_theory.md``::

    T = C^E S - e.T E
    D = e S + epsilon^S E

The input piezoelectric matrix must therefore be the *proper* thermodynamic
``e`` tensor at fixed electric field.  A raw Berry finite-difference tensor is
not silently accepted: callers must apply the explicit proper correction first.
No calculator-specific sign, Voigt, or unit convention is inferred here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from .mechanical import ENGINEERING_VOIGT
from .model import BoundaryConditions, TensorQuantity
from .units import convert_dielectric, convert_values


def _finite_matrix(value: Any, shape: tuple[int, ...], name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape:
        raise ValueError(f"{name} must have shape {shape}; got {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values")
    return array.copy()


def _symmetric_or_error(matrix: np.ndarray, name: str, tolerance: float) -> np.ndarray:
    mismatch = float(np.max(np.abs(matrix - matrix.T)))
    scale = max(float(np.max(np.abs(matrix))), 1.0)
    if mismatch > float(tolerance) * scale:
        raise ValueError(
            f"{name} must be symmetric in the thermodynamic convention; "
            f"maximum antisymmetric part is {mismatch:.6g}"
        )
    return 0.5 * (matrix + matrix.T)


def _inverse(matrix: np.ndarray, name: str) -> tuple[np.ndarray, float]:
    try:
        inverse = np.linalg.inv(matrix)
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"{name} is singular; cannot form its reciprocal response") from exc
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    if singular_values.size == 0 or singular_values[-1] == 0.0:
        raise ValueError(f"{name} is singular; cannot form its reciprocal response")
    return inverse, float(singular_values[0] / singular_values[-1])


def _convert_piezoelectric(values: Any, unit: str) -> np.ndarray:
    """Convert the explicitly supported piezoelectric unit to C/m^2."""

    canonical = "".join(str(unit).strip().lower().split())
    aliases = {"c/m^2", "c/m2", "c·m^-2", "c*m^-2", "coulomb/m^2"}
    if canonical not in aliases:
        raise ValueError(
            "piezoelectric_unit must be explicitly expressed as C/m^2; "
            f"got {unit!r}"
        )
    array = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(array)):
        raise ValueError("piezoelectric tensor contains non-finite values")
    return array.copy()


@dataclass(frozen=True)
class ElectromechanicalForms:
    """All reciprocal piezoelectric forms in a fixed SI convention.

    Matrix axes are ``(electric/polarization, engineering-Voigt)`` for
    ``e``, ``d``, ``g`` and ``h``.  ``C``/``s`` use Voigt row/column order and
    ``epsilon``/``beta`` use Cartesian electric axes.  The dielectric tensors
    are absolute (F/m), elastic tensors are Pa/GPa-independent SI (Pa), and
    the piezoelectric matrices use C/m^2, C/N, V m/N and V/m respectively.
    ``diagnostics`` contains reciprocal-identity residuals and condition
    numbers; it is deliberately numeric rather than a calculator-specific
    output object.
    """

    e: np.ndarray
    d: np.ndarray
    g: np.ndarray
    h: np.ndarray
    c_e: np.ndarray
    c_d: np.ndarray
    s_e: np.ndarray
    s_d: np.ndarray
    epsilon_s: np.ndarray
    epsilon_t: np.ndarray
    beta_s: np.ndarray
    beta_t: np.ndarray
    voigt_convention: tuple[str, ...]
    diagnostics: Mapping[str, float]

    def __post_init__(self) -> None:
        for name in (
            "e", "d", "g", "h",
        ):
            value = np.asarray(getattr(self, name), dtype=float)
            if value.shape != (3, 6) or not np.all(np.isfinite(value)):
                raise ValueError(f"{name} must be a finite (3, 6) matrix")
            object.__setattr__(self, name, value)
        for name in (
            "c_e", "c_d", "s_e", "s_d",
        ):
            value = np.asarray(getattr(self, name), dtype=float)
            if value.shape != (6, 6) or not np.all(np.isfinite(value)):
                raise ValueError(f"{name} must be a finite (6, 6) matrix")
            object.__setattr__(self, name, value)
        for name in ("epsilon_s", "epsilon_t", "beta_s", "beta_t"):
            value = np.asarray(getattr(self, name), dtype=float)
            if value.shape != (3, 3) or not np.all(np.isfinite(value)):
                raise ValueError(f"{name} must be a finite (3, 3) matrix")
            object.__setattr__(self, name, value)
        convention = tuple(str(item) for item in self.voigt_convention)
        if convention != ENGINEERING_VOIGT:
            raise ValueError(
                "electromechanical conversions currently require engineering "
                f"Voigt convention {ENGINEERING_VOIGT}; got {convention}"
            )
        object.__setattr__(self, "voigt_convention", convention)
        object.__setattr__(self, "diagnostics", dict(self.diagnostics))

    def to_tensor_quantities(
        self,
        *,
        backend: str,
        source: str = "thermodynamic_conversion",
        periodic_axes: tuple[str, ...] = ("x", "y", "z"),
        ion_relaxation: str = "clamped-ion",
        normalization: str = "cell_volume",
        provenance: Mapping[str, Any] | None = None,
    ) -> tuple[TensorQuantity, ...]:
        """Materialize the forms as explicitly annotated v2 quantities.

        This method does not create a :class:`~zstar.v2.model.ResponseDocument`
        because dimensionality and structure belong to the caller.  It does,
        however, attach the thermodynamic electric/mechanical boundary to each
        quantity so that ``d`` is not confused with ``e`` and ``C^D`` is not
        confused with ``C^E``.  The caller must still place the returned tuple
        in a document whose ``periodic_axes`` match ``periodic_axes``.
        """

        if not str(backend).strip():
            raise ValueError("backend must not be empty")
        if not str(source).strip():
            raise ValueError("source must not be empty")
        axes = tuple(str(axis).strip().lower() for axis in periodic_axes)
        if len(set(axes)) != len(axes) or any(axis not in {"x", "y", "z"} for axis in axes):
            raise ValueError(f"periodic_axes must be unique members of ('x', 'y', 'z'); got {axes}")
        if ion_relaxation not in {"clamped-ion", "relaxed-ion", "internal-contribution", "not-applicable"}:
            raise ValueError(f"unsupported ion_relaxation {ion_relaxation!r}")
        shared_provenance = {
            "conversion": "zstar.v2.convert_piezoelectric_forms",
            "input_piezoelectric_kind": "proper",
            "voigt_convention": list(ENGINEERING_VOIGT),
            **dict(provenance or {}),
        }

        def quantity(
            name: str,
            values: np.ndarray,
            unit: str,
            *,
            boundary: BoundaryConditions,
            axes_: tuple[str, ...],
        ) -> TensorQuantity:
            return TensorQuantity(
                name=name,
                values=values,
                unit=unit,
                axes=axes_,
                coordinate_system="cartesian_right_handed",
                voigt_convention=ENGINEERING_VOIGT if "voigt" in axes_ else (),
                ion_relaxation=ion_relaxation,
                boundary_conditions=boundary,
                periodic_axes=axes,
                normalization=normalization,
                source=source,
                backend=backend,
                provenance=shared_provenance,
                diagnostics=self.diagnostics,
            )

        return (
            quantity(
                "piezoelectric_e", self.e, "C/m^2",
                boundary=BoundaryConditions(electric="E", mechanical="strain"),
                axes_=("electric", "voigt_engineering"),
            ),
            quantity(
                "piezoelectric_d", self.d, "C/N",
                boundary=BoundaryConditions(electric="E", mechanical="stress"),
                axes_=("electric", "voigt_engineering"),
            ),
            quantity(
                "piezoelectric_g", self.g, "V m/N",
                boundary=BoundaryConditions(electric="D", mechanical="stress"),
                axes_=("electric", "voigt_engineering"),
            ),
            quantity(
                "piezoelectric_h", self.h, "V/m",
                boundary=BoundaryConditions(electric="D", mechanical="strain"),
                axes_=("electric", "voigt_engineering"),
            ),
            quantity(
                "elastic_CE", self.c_e, "Pa",
                boundary=BoundaryConditions(electric="E", mechanical="strain"),
                axes_=("stress_voigt", "voigt_engineering"),
            ),
            quantity(
                "elastic_CD", self.c_d, "Pa",
                boundary=BoundaryConditions(electric="D", mechanical="strain"),
                axes_=("stress_voigt", "voigt_engineering"),
            ),
            quantity(
                "compliance_sE", self.s_e, "Pa^-1",
                boundary=BoundaryConditions(electric="E", mechanical="stress"),
                axes_=("strain_voigt", "stress_voigt"),
            ),
            quantity(
                "compliance_sD", self.s_d, "Pa^-1",
                boundary=BoundaryConditions(electric="D", mechanical="stress"),
                axes_=("strain_voigt", "stress_voigt"),
            ),
            quantity(
                "dielectric_epsilonS", self.epsilon_s, "F/m",
                boundary=BoundaryConditions(electric="E", mechanical="strain"),
                axes_=("electric_row", "electric_column"),
            ),
            quantity(
                "dielectric_epsilonT", self.epsilon_t, "F/m",
                boundary=BoundaryConditions(electric="E", mechanical="stress"),
                axes_=("electric_row", "electric_column"),
            ),
            quantity(
                "impermittivity_betaS", self.beta_s, "m/F",
                boundary=BoundaryConditions(electric="E", mechanical="strain"),
                axes_=("electric_row", "electric_column"),
            ),
            quantity(
                "impermittivity_betaT", self.beta_t, "m/F",
                boundary=BoundaryConditions(electric="E", mechanical="stress"),
                axes_=("electric_row", "electric_column"),
            ),
        )


def convert_piezoelectric_forms(
    e: Any,
    elastic: Any,
    dielectric: Any,
    *,
    piezoelectric_unit: str = "C/m^2",
    elastic_unit: str = "Pa",
    dielectric_unit: str = "F/m",
    piezoelectric_kind: str = "proper",
    voigt_convention: tuple[str, ...] = ENGINEERING_VOIGT,
    symmetry_tolerance: float = 1.0e-10,
) -> ElectromechanicalForms:
    """Convert thermodynamic ``e`` to ``d``, ``g`` and ``h`` forms.

    Parameters are explicitly unit-labelled.  ``dielectric_unit`` may be
    ``F/m`` or ``relative``; relative values are multiplied by the v2
    ``epsilon_0`` constant.  ``elastic`` is converted to Pa using the shared
    pressure conversion table.  The supported piezoelectric input is C/m^2.

    The input ``e`` must be a *proper* tensor in the engineering-Voigt order
    ``(xx, yy, zz, 2yz, 2xz, 2xy)``.  Passing ``piezoelectric_kind='raw'`` or
    another unspecified kind fails instead of treating an improper Berry
    derivative as a thermodynamic coefficient.
    """

    if piezoelectric_kind != "proper":
        raise ValueError(
            "convert_piezoelectric_forms requires piezoelectric_kind='proper'; "
            "apply proper_piezoelectric_response explicitly to a raw Berry derivative"
        )
    convention = tuple(str(item) for item in voigt_convention)
    if convention != ENGINEERING_VOIGT:
        raise ValueError(
            "electromechanical conversions currently require engineering "
            f"Voigt convention {ENGINEERING_VOIGT}; got {convention}"
        )
    if not np.isfinite(symmetry_tolerance) or float(symmetry_tolerance) < 0.0:
        raise ValueError("symmetry_tolerance must be finite and non-negative")

    e_si = _finite_matrix(_convert_piezoelectric(e, piezoelectric_unit), (3, 6), "e")
    c_si = _finite_matrix(convert_values(elastic, elastic_unit, "Pa"), (6, 6), "elastic")
    eps_si = _finite_matrix(
        convert_dielectric(dielectric, dielectric_unit, "F/m"), (3, 3), "dielectric"
    )
    c_si = _symmetric_or_error(c_si, "elastic", float(symmetry_tolerance))
    eps_si = _symmetric_or_error(eps_si, "dielectric", float(symmetry_tolerance))

    s_e, cond_c_e = _inverse(c_si, "elastic C^E")
    beta_s, cond_eps_s = _inverse(eps_si, "dielectric epsilon^S")
    d = e_si @ s_e
    eps_t = _symmetric_or_error(eps_si + e_si @ s_e @ e_si.T, "epsilon^T", float(symmetry_tolerance))
    beta_t, cond_eps_t = _inverse(eps_t, "dielectric epsilon^T")
    g = beta_t @ d
    h = beta_s @ e_si
    c_d = _symmetric_or_error(c_si + e_si.T @ beta_s @ e_si, "elastic C^D", float(symmetry_tolerance))
    s_d, cond_c_d = _inverse(c_d, "elastic C^D")

    residuals = {
        "e_minus_d_c_e_max": float(np.max(np.abs(e_si - d @ c_si))),
        "d_minus_e_s_e_max": float(np.max(np.abs(d - e_si @ s_e))),
        "d_minus_epsilon_t_g_max": float(np.max(np.abs(d - eps_t @ g))),
        "h_minus_beta_s_e_max": float(np.max(np.abs(h - beta_s @ e_si))),
        "h_minus_g_c_d_max": float(np.max(np.abs(h - g @ c_d))),
        "epsilon_t_minus_reconstructed_max": float(
            np.max(np.abs(eps_t - (eps_si + e_si @ s_e @ e_si.T)))
        ),
        "c_d_minus_reconstructed_max": float(
            np.max(np.abs(c_d - (c_si + e_si.T @ beta_s @ e_si)))
        ),
        "condition_c_e": cond_c_e,
        "condition_c_d": cond_c_d,
        "condition_epsilon_s": cond_eps_s,
        "condition_epsilon_t": cond_eps_t,
    }
    return ElectromechanicalForms(
        e=e_si,
        d=d,
        g=g,
        h=h,
        c_e=c_si,
        c_d=c_d,
        s_e=s_e,
        s_d=s_d,
        epsilon_s=eps_si,
        epsilon_t=eps_t,
        beta_s=beta_s,
        beta_t=beta_t,
        voigt_convention=convention,
        diagnostics=residuals,
    )
