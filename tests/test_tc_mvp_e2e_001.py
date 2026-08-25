from __future__ import annotations

import json
from pathlib import Path

from scripts import run_tc_mvp_e2e_001 as e2e


def test_sim_passes_without_real_effects(tmp_path: Path) -> None:
    report = tmp_path / "sim.json"
    assert e2e.run_sim(report) == []
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["test_id"] == "TC-MVP-E2E-001-SIM"
    assert payload["execution_provider"] == "fake"
    assert payload["sim_passed"] is True
    assert payload["real_acceptance_satisfied"] is False
    assert all(value == 0 for value in payload["effect_traps"].values())


def test_real_preflight_requires_passing_sim(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    errors = e2e.run_real_preflight(missing)
    assert "SIM evidence is missing" in errors

    report = tmp_path / "sim.json"
    assert e2e.run_sim(report) == []
    assert e2e.run_real_preflight(report) == []


def test_sim_cannot_claim_real_acceptance(tmp_path: Path) -> None:
    report = tmp_path / "sim.json"
    assert e2e.run_sim(report) == []
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["real_acceptance_satisfied"] = True
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert "SIM evidence incorrectly claims REAL acceptance" in e2e.run_real_preflight(report)
