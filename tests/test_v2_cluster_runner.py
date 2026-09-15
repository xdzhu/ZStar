from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "tools" / "v2_piezo_235_direct.sh"
HF_RUNNER = Path(__file__).resolve().parents[1] / "tools" / "v2_piezo_hf.slurm"
HF_REFERENCE_RUNNER = Path(__file__).resolve().parents[1] / "tools" / "v2_ref_relax_hf.slurm"


def test_relaxed_235_runner_enforces_tight_protocol_and_ionic_convergence():
    text = RUNNER.read_text(encoding="utf-8")

    assert "v2 requires symmetry_prec=1e-3" in text
    assert "v2 perturbation requires symmetry=0" in text
    assert 'read -r -a requested_stages <<< "${ZSTAR_STAGE_IDS//,/ }"' in text
    assert "force_thr_ev <= 1e-6 requires scf_thr <= 1e-10" in text
    assert "invalid or missing relax_nmax" in text
    assert "grep -qi 'relaxation is converged'" in text
    assert '"$d"/OUT.*/running_relax.log' in text
    assert (
        "charge density convergence is achieved|relaxation is converged|calculation *finished"
        not in text
    )


def test_hf_runners_enforce_reference_and_response_precision_protocols():
    reference = HF_REFERENCE_RUNNER.read_text(encoding="utf-8")
    response = HF_RUNNER.read_text(encoding="utf-8")

    assert 'NP="${ZSTAR_MPI_RANKS:-32}"' in reference
    assert "calculation=cell-relax" in reference
    assert "symmetry_prec=1e-3" in reference
    assert "force_thr_ev<=1e-4" in reference
    assert "stress_thr<=0.1 kbar" in reference
    assert "scf_thr<=1e-10" in reference
    assert "relax_nmax>=100" in reference
    assert "relaxation is converged" in reference

    assert 'NP="${ZSTAR_MPI_RANKS:-32}"' in response
    assert "symmetry_prec=1e-3" in response
    assert "v2 reference requires symmetry=1" in response
    assert "v2 perturbations require symmetry=0" in response
    assert 'require_leq "$input" force_thr_ev 1e-6' in response
    assert "relax_nmax>=100" in response
