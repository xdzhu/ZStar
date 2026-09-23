from pathlib import Path

import pytest

from zstar.insulation import parse_abacus_occupation_gap


def _write_istate(path: Path, blocks: list[list[tuple[float, float]]]) -> Path:
    lines: list[str] = []
    for kpoint, rows in enumerate(blocks, start=1):
        lines.append(f"BAND Energy(ev) Occupation Kpoint = {kpoint}")
        for band, (energy, occupation) in enumerate(rows, start=1):
            lines.append(f"{band:6d} {energy:16.8f} {occupation:16.8f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_full_mesh_gap_records_constant_occupied_manifold(tmp_path):
    path = _write_istate(
        tmp_path / "istate.info",
        [
            [(-3.0, 0.125), (1.0, 0.125), (3.5, 0.0)],
            [(-2.8, 0.125), (1.4, 0.125), (3.1, 0.0)],
        ],
    )
    result = parse_abacus_occupation_gap(path)
    assert result is not None
    assert result["insulating"] is True
    assert result["gap_eV"] == pytest.approx(1.7)
    assert result["kpoint_count"] == 2
    assert result["occupied_band_count"] == 2
    assert result["occupied_band_count_consistent"] is True
    assert result["fractional_occupation_count"] == 0


def test_full_mesh_gap_rejects_changed_occupied_band_count(tmp_path):
    path = _write_istate(
        tmp_path / "istate.info",
        [
            [(-3.0, 0.125), (1.0, 0.125), (3.5, 0.0)],
            [(-2.8, 0.125), (1.4, 0.0), (3.1, 0.0)],
        ],
    )
    result = parse_abacus_occupation_gap(path)
    assert result is not None
    assert result["insulating"] is False
    assert result["occupied_band_count"] is None
    assert result["occupied_band_count_consistent"] is False


def test_full_mesh_gap_rejects_fractional_occupation(tmp_path):
    path = _write_istate(
        tmp_path / "istate.info",
        [[(-3.0, 0.125), (1.0, 0.0625), (3.5, 0.0)]],
    )
    result = parse_abacus_occupation_gap(path)
    assert result is not None
    assert result["insulating"] is False
    assert result["fractional_occupation_count"] == 1


def test_small_smearing_tail_is_treated_as_empty(tmp_path):
    path = _write_istate(
        tmp_path / "istate.info",
        [[(-3.0, 0.125), (1.0, 0.125), (3.5, 1.0e-9)]],
    )
    result = parse_abacus_occupation_gap(path)
    assert result is not None
    assert result["insulating"] is True
    assert result["occupied_band_count"] == 2
    assert result["fractional_occupation_count"] == 0
