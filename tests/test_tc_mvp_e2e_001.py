from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts import run_tc_mvp_e2e_001 as e2e


def _target_root() -> Path:
    raw = os.environ.get(e2e.TARGET_ROOT_ENV)
    if not raw:
        pytest.skip("immutable consulting-playbook adapter checkout not available")
    root = Path(raw)
    if not root.is_dir():
        pytest.skip("immutable consulting-playbook adapter checkout not available")
    return root


def test_sim_passes_without_real_effects(tmp_path: Path) -> None:
    target_root = _target_root()
    report = tmp_path / "sim.json"
    assert e2e.run_sim(report, target_root) == []
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["test_id"] == "TC-MVP-E2E-001-SIM"
    assert payload["published_baseline"] == "2.3.2"
    assert payload["candidate_release"] == "2.4.0"
    assert payload["candidate_tag_published"] is False
    assert payload["execution_provider"] == "fake"
    assert payload["target"] == e2e.REAL_TARGET
    assert payload["shared_target_adapter_path"] is True
    assert payload["shared_receiver_path"] is True
    assert payload["sim_passed"] is True
    assert payload["real_acceptance_satisfied"] is False
    assert payload["primary_execution_status"] == "draft-pr-created"
    assert payload["duplicate_execution_status"] == "duplicate-reused"
    assert payload["receiver_forward_count"] == 1
    assert payload["conflicting_duplicate_result"] == "ambiguous-rejected"
    assert all(value == 0 for value in payload["effect_traps"].values())


def test_real_preflight_fails_closed_until_release_and_target_pin_are_ready(tmp_path: Path) -> None:
    target_root = _target_root()
    missing = tmp_path / "missing.json"
    errors = e2e.run_real_preflight(missing, target_root)
    assert "SIM evidence is missing" in errors

    report = tmp_path / "sim.json"
    assert e2e.run_sim(report, target_root) == []
    errors = e2e.run_real_preflight(report, target_root)
    assert "ai-sdlc-v2.4.0 is not published; REAL remains blocked" in errors
    assert "enabled target is not pinned to the ai-sdlc-v2.4.0 receiver" in errors


def test_sim_cannot_claim_real_acceptance(tmp_path: Path) -> None:
    target_root = _target_root()
    report = tmp_path / "sim.json"
    assert e2e.run_sim(report, target_root) == []
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["real_acceptance_satisfied"] = True
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert "SIM evidence incorrectly claims REAL acceptance" in e2e.run_real_preflight(
        report, target_root
    )


def test_real_preflight_requires_shared_receiver_evidence(tmp_path: Path) -> None:
    target_root = _target_root()
    report = tmp_path / "sim.json"
    assert e2e.run_sim(report, target_root) == []
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["shared_receiver_path"] = False
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert "SIM evidence did not exercise the shared target and receiver paths" in e2e.run_real_preflight(
        report, target_root
    )
