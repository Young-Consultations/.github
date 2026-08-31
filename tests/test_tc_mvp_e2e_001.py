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
    assert payload["published_baseline"] == "2.4.0"
    assert payload["candidate_release"] == "2.4.1"
    assert payload["candidate_tag_published"] is True
    assert payload["execution_provider"] == "fake"
    assert payload["dispatch_provider"] == "fake-in-process-target"
    assert payload["target"] == e2e.REAL_TARGET
    assert payload["shared_router_path"] is True
    assert payload["shared_target_adapter_path"] is True
    assert payload["shared_receiver_path"] is True
    assert payload["router_validation_result"] == "passed"
    assert payload["task_id"] == payload["delivery_id"] == payload["correlation_id"]
    assert payload["source_issue"]
    assert payload["control_plane_commit"]
    assert payload["sim_passed"] is True
    assert payload["real_acceptance_satisfied"] is False
    assert payload["primary_execution_status"] == "draft-pr-created"
    assert payload["duplicate_execution_status"] == "duplicate-reused"
    assert payload["first_receiver_receipt"] == "accepted"
    assert payload["duplicate_receiver_receipt"] == "accepted-duplicate"
    assert payload["receiver_forward_count"] == 1
    assert payload["conflicting_duplicate_result"] == "ambiguous-rejected"
    assert payload["primary_fake_effect_calls"] == {
        "discover_calls": 1,
        "codex_calls": 1,
        "validation_calls": 1,
        "publication_calls": 1,
    }
    assert payload["duplicate_fake_effect_calls"] == {
        "discover_calls": 1,
        "codex_calls": 0,
        "validation_calls": 0,
        "publication_calls": 0,
    }
    assert all(value == 0 for value in payload["effect_traps"].values())
    assert payload["failures"] == []


def test_target_identity_mismatch_fails_before_adapter_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_root = _target_root()
    imported = False

    def forbidden_import(root: Path):
        nonlocal imported
        imported = True
        raise AssertionError("mismatched target must never be imported")

    monkeypatch.setattr(e2e, "_target_identity_errors", lambda root: ["identity mismatch"])
    monkeypatch.setattr(e2e, "_load_target_adapter", forbidden_import)
    errors = e2e.run_sim(tmp_path / "sim.json", target_root)
    assert "identity mismatch" in errors
    assert imported is False


def test_target_identity_git_failure_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    target_root = _target_root()
    original = e2e._git_output

    def failing_git(args: list[str], cwd: Path = e2e.ROOT):
        if cwd == target_root and args == ["rev-parse", "HEAD"]:
            return None, "git unavailable"
        return original(args, cwd)

    monkeypatch.setattr(e2e, "_git_output", failing_git)
    assert e2e._target_identity_errors(target_root) == [
        "target checkout identity cannot be read: git unavailable"
    ]


def test_publication_identity_compares_tag_with_attested_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = "34ec7dc1cf54f960757781851384e0f6b15f7b63"
    monkeypatch.setattr(e2e, "_git_output", lambda args, cwd=e2e.ROOT: (expected, None))
    assert e2e._control_plane_release_identity_errors() == []

    actual = "0" * 40
    monkeypatch.setattr(e2e, "_git_output", lambda args, cwd=e2e.ROOT: (actual, None))
    assert e2e._control_plane_release_identity_errors() == [
        f"published tag ai-sdlc-v2.4.1 resolves to {actual}, not attested commit {expected}"
    ]


def test_publication_identity_rejects_missing_attestation_before_tag_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(e2e, "_load", lambda path: {"tag_commit_sha": None})

    def forbidden_git(*args, **kwargs):
        raise AssertionError("tag lookup must not run without a valid attestation")

    monkeypatch.setattr(e2e, "_git_output", forbidden_git)
    assert e2e._control_plane_release_identity_errors() == [
        "published release must record a valid immutable tag commit SHA "
        "before tag identity can be verified"
    ]


def test_real_preflight_passes_for_published_release_when_identity_is_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_root = _target_root()
    monkeypatch.setattr(e2e, "_real_release_errors", lambda: [])
    monkeypatch.setattr(e2e, "_target_identity_errors", lambda root: [])
    monkeypatch.setattr(e2e, "_target_receiver_pin_errors", lambda root: [])

    missing = tmp_path / "missing.json"
    errors = e2e.run_real_preflight(missing, target_root)
    assert "SIM evidence is missing" in errors

    report = tmp_path / "sim.json"
    assert e2e.run_sim(report, target_root) == []
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["control_plane_commit"] = "34ec7dc1cf54f960757781851384e0f6b15f7b63"
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert e2e.run_real_preflight(report, target_root) == []


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


def test_real_preflight_requires_full_shared_path_evidence(tmp_path: Path) -> None:
    target_root = _target_root()
    report = tmp_path / "sim.json"
    assert e2e.run_sim(report, target_root) == []
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["shared_router_path"] = False
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert (
        "SIM evidence did not exercise the shared router, target, and receiver paths"
        in e2e.run_real_preflight(report, target_root)
    )


def test_real_preflight_rejects_tampered_effect_evidence(tmp_path: Path) -> None:
    target_root = _target_root()
    report = tmp_path / "sim.json"
    assert e2e.run_sim(report, target_root) == []
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["effect_traps"]["real_pull_requests_created"] = 1
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert "SIM evidence does not prove zero prohibited real effects" in e2e.run_real_preflight(
        report, target_root
    )


def test_real_preflight_rejects_stale_control_plane_evidence(tmp_path: Path) -> None:
    target_root = _target_root()
    report = tmp_path / "sim.json"
    assert e2e.run_sim(report, target_root) == []
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["control_plane_commit"] = "0" * 40
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert (
        "SIM evidence does not match the attested immutable control plane/REAL target/adapter"
        in e2e.run_real_preflight(report, target_root)
    )
