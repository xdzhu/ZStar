import json
from pathlib import Path
import subprocess

from zstar.abacus_assets import prepare_stru_assets


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def _manifest_cases():
    manifest = json.loads((EXAMPLES / "manifest.json").read_text(encoding="utf-8"))
    return manifest["cases"]


def test_manifest_cases_are_self_describing():
    for record in _manifest_cases():
        case = EXAMPLES / record["path"]
        assert case.is_dir(), record["id"]
        assert (case / "run.sh").is_file(), record["id"]
        assert (case / "README.md").is_file(), record["id"]
        assert (case / "README.zh-CN.md").is_file(), record["id"]
        assert (case / "run").is_dir(), record["id"]
        assert any(p.is_file() for p in (case / "run").rglob("*")), record["id"]
        assert (case / "results").is_dir(), record["id"]
        assert any((case / "results").rglob("*")), record["id"]


def test_manifest_paths_match_git_index_case():
    if not (ROOT / ".git").exists():
        return
    tracked = set(subprocess.check_output(
        ["git", "ls-files", "-z", "--", "examples"], cwd=ROOT
    ).decode("utf-8").split("\0"))
    for record in _manifest_cases():
        path = f"examples/{record['path']}/run.sh"
        assert path in tracked, f"Case-sensitive Git path missing: {path}"


def test_abacus_cases_ship_matching_assets(tmp_path):
    for record in _manifest_cases():
        if not record["calculator"].startswith("ABACUS"):
            continue
        case = EXAMPLES / record["path"]
        if record.get("assets_required") is False:
            continue
        run = case / "run"
        assets = run / "assets"
        asset_root = assets if any(assets.glob("*.upf")) else run
        prepared = prepare_stru_assets(
            run / "STRU", pp_dir=asset_root, orb_dir=asset_root,
            output_dir=tmp_path / record["id"],
        )
        assert any(p.suffix.lower() == ".upf" for p in prepared.assets), record["id"]
        assert any(p.suffix.lower() == ".orb" for p in prepared.assets), record["id"]


def test_backend_cases_declare_external_asset_boundary():
    for record in _manifest_cases():
        if record["calculator"].startswith("ABACUS"):
            continue
        case = EXAMPLES / record["path"]
        metadata = json.loads((case / "case.json").read_text(encoding="utf-8"))
        provenance = case / "ASSET_PROVENANCE.md"
        assert provenance.is_file(), record["id"]
        if record["calculator"] == "VASP":
            assert metadata["licensed_inputs_required"]
        if record["calculator"] == "CP2K":
            assert metadata["data_dir_required"] is True


def test_legacy_case_layout_is_not_reintroduced():
    legacy_names = {"input", "reference_results", "reference_spectroscopy"}
    for path in EXAMPLES.rglob("*"):
        if path.is_dir():
            assert path.name not in legacy_names, path


def test_run_directories_contain_inputs_only():
    allowed_asset_dirs = {"assets", "pp", "orb", "relaxation", "vasp"}
    for record in _manifest_cases():
        run_dir = EXAMPLES / record["path"] / "run"
        unexpected = [
            path for path in run_dir.rglob("*")
            if path.is_dir() and path.name not in allowed_asset_dirs
        ]
        assert not unexpected, (record["id"], unexpected)
        assert not (run_dir / "work").exists(), record["id"]
        assert not (run_dir / "native").exists(), record["id"]
        vasp = run_dir / "vasp"
        if vasp.is_dir():
            assert {p.name for p in vasp.iterdir()} == {
                "INCAR", "KPOINTS", "POSCAR", "input_provenance.json"}, record["id"]
            assert all(p.is_file() for p in vasp.iterdir()), record["id"]
            provenance = json.loads((vasp / "input_provenance.json").read_text(encoding="utf-8"))
            assert provenance["potential_redistribution"] is False, record["id"]
            assert len(provenance["potential_sha256"]) == 2, record["id"]
        relaxation = run_dir / "relaxation"
        if relaxation.is_dir():
            assert {p.name for p in relaxation.iterdir()} <= {
                "INPUT", "KPT", "STRU", "structure.vasp", "assets"}, record["id"]
            assert all(p.is_file() or p.name == "assets" for p in relaxation.iterdir()), record["id"]
            assert all(p.is_file() and p.suffix.lower() in {".upf", ".orb"}
                       for p in (relaxation / "assets").glob("*")), record["id"]
