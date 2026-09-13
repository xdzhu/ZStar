from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path("examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/run").resolve()))

from prepare_cubic_supercell_supplement import (  # noqa: E402
    build_supplement,
    read_extxyz,
)


def test_cubic_supercell_supplement_is_50_frames_with_phonon_seed(tmp_path: Path):
    source = Path("examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/results/qnep_training/cubic_104_seed20260913/phonopy_inputs")
    manifest = build_supplement(source, tmp_path / "supplement", seed=20260913, target_count=50)
    frames = read_extxyz(tmp_path / "supplement" / "geometry_candidates.xyz")
    assert manifest["actual_frames"] == 50
    assert len(frames) == 50
    assert {len(frame.symbols) for frame in frames} == {40}
    assert [frame.frame_id for frame in frames[:4]] == [
        "phonon_equilibrium",
        "phonon_disp_001",
        "phonon_disp_002",
        "phonon_disp_003",
    ]
    assert manifest["exchange_correlation"] == "PBEsol"
    assert manifest["kspacing_inv_bohr"] == 0.1
    assert manifest["geometry_reuse_policy"].startswith("reuse_existing_phonon_geometry_and_labels")
    assert manifest["new_force_label_frames"] == 46
    assert manifest["reused_existing_phonon_frames"] == 4
    saved = json.loads((tmp_path / "supplement" / "manifest.json").read_text())
    assert saved["actual_frames"] == 50
