from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "tools" / "v2_piezo_235_direct.sh"
HF_RUNNER = Path(__file__).resolve().parents[1] / "tools" / "v2_piezo_hf.slurm"
HF_REFERENCE_RUNNER = Path(__file__).resolve().parents[1] / "tools" / "v2_ref_relax_hf.slurm"


def test_relaxed_235_runner_enforces_fixed_protocol_and_ionic_convergence():
    text = RUNNER.read_text(encoding="utf-8")

    assert "requires symmetry_prec=1e-3" not in text
    assert "v2 perturbation requires symmetry=0" in text
    assert 'read -r -a requested_stages <<< "${ZSTAR_STAGE_IDS//,/ }"' in text
    assert "v2 fixed protocol requires force_thr_ev=1e-4" in text
    assert "v2 fixed protocol requires scf_thr=1e-8" in text
    assert "invalid or missing relax_nmax" in text
    assert "grep -qi 'relaxation is converged'" in text
    assert '"$d"/OUT.*/running_relax.log' in text
    assert (
        "charge density convergence is achieved|relaxation is converged|calculation *finished"
        not in text
    )


def test_hf_runners_enforce_matching_production_or_verification_profiles():
    reference = HF_REFERENCE_RUNNER.read_text(encoding="utf-8")
    response = HF_RUNNER.read_text(encoding="utf-8")

    assert 'NP="${ZSTAR_MPI_RANKS:-32}"' in reference
    assert 'PROFILE="${ZSTAR_V2_CONVERGENCE_PROFILE:-production}"' in reference
    assert "production|verification) MAX_FORCE=1e-4; MAX_STRESS=0.5; MAX_SCF=1e-8" in reference
    assert "calculation=cell-relax" in reference
    assert 'PROFILE_MARKER="$ROOT/convergence_profile.txt"' in reference
    assert 'EXPECTED_PROFILE=$(tr -d' in reference
    assert "symmetry_prec=1e-3" not in reference
    assert "force_thr_ev=$MAX_FORCE" in reference
    assert "stress_thr=$MAX_STRESS kbar" in reference
    assert "scf_thr=$MAX_SCF" in reference
    assert "relax_nmax>=100" in reference
    assert "relaxation is converged" in reference
    assert "running_cell-relax.log" in reference
    assert "running_relax.log" in reference

    assert 'NP="${ZSTAR_MPI_RANKS:-32}"' in response
    assert 'PROFILE="${ZSTAR_V2_CONVERGENCE_PROFILE:-production}"' in response
    assert "production|verification) MAX_SCF=1e-8; MAX_RELAX_FORCE=1e-4" in response
    assert "symmetry_prec=1e-3" not in response
    assert 'PROFILE_MARKER="$ROOT/convergence_profile.txt"' in response
    assert "v2 reference requires symmetry=1" in response
    assert "v2 perturbations require symmetry=0" in response
    assert 'require_equal "$input" force_thr_ev "$MAX_RELAX_FORCE"' in response
    assert "relax_nmax>=100" in response
