from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "tools" / "v2_piezo_235_direct.sh"


def test_relaxed_235_runner_enforces_tight_protocol_and_ionic_convergence():
    text = RUNNER.read_text(encoding="utf-8")

    assert "v2 requires symmetry_prec=1e-3" in text
    assert 'read -r -a requested_stages <<< "${ZSTAR_STAGE_IDS//,/ }"' in text
    assert "force_thr_ev <= 1e-6 requires scf_thr <= 1e-10" in text
    assert "invalid or missing relax_nmax" in text
    assert "grep -qi 'relaxation is converged'" in text
    assert '"$d"/OUT.*/running_relax.log' in text
    assert (
        "charge density convergence is achieved|relaxation is converged|calculation *finished"
        not in text
    )
