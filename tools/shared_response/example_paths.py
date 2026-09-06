"""Locate published benchmark cases without making workflow names a taxonomy."""
from pathlib import Path

CASE_PATHS = {
    'cubic_BaTiO3': '3D_Bulk/cubic_BaTiO3',
    'SiC': '3D_Bulk/SiC',
    't_HfO2': '3D_Bulk/t_HfO2',
    'alpha_In2Se3': '2D_Slab/alpha_In2Se3_PBE',
    'hBN': '2D_Slab/hBN_unified',
    'MoS2': '2D_Slab/MoS2_unified',
    'H2O': '0D_Molecules/H2O_unified',
    'CH4': '0D_Molecules/CH4_unified',
}


def case_path(root: Path, name: str) -> Path:
    """Accept the public Benchmarks index or an untouched remote archive root."""
    legacy = root / name
    return legacy if legacy.is_dir() else root.parent / CASE_PATHS[name]
