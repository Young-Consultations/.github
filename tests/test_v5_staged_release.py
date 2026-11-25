"""Offline structural verification of the non-deployable v5 overlay."""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from scripts import generate_current_runtime, validate_release

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "release/staged-v5"
TARGET = "Young-Consultations/consulting-playbook"
OVERLAY = STAGE / "overlay"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_staged_binding_is_not_release_attestation():
    binding = load(STAGE / "binding.json")
    manifest = load(OVERLAY / "release/release-manifest.json")
    registry = load(OVERLAY / "config/codex-repositories.json")
    report_path = STAGE / "evidence/target-report.json"
    report = load(report_path)
    pin = load(STAGE / "evidence/target-pin.json")
    assert binding["status"] == "BLOCKED_UNPUBLISHED_BINDINGS"
    assert binding["control_plane"]["resolved_commit_sha"] is None
    assert binding["adapter"]["resolved_tag_commit_sha"] is None
    assert binding["production_readiness_claim"] is False
    assert binding["activation_requested"] is False
    assert manifest["release_version"] == "5.0.0"
    assert manifest["tag_published"] is False and manifest["tag_commit_sha"] is None
    entry = registry["repositories"][TARGET]
    evidence = entry["conformance"]
    assert evidence["adapter_commit_sha"] == binding["adapter"]["reviewed_merge_commit"]
    assert evidence["adapter_ref"] == binding["adapter"]["proposed_tag"]
    assert evidence["report_sha256"] == binding["adapter"]["report_sha256"] == digest(report_path)
    raw = report_path.read_bytes()
    assert hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() == binding["adapter"]["report_git_blob_sha"]
    revision = pin["adapter_revision"]
    pin["adapter_revision"] = None
    assert revision == "sha256:" + hashlib.sha256(
        json.dumps(pin, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert revision == report["adapter_revision"] == binding["adapter"]["conformance_revision"]
    assert report["production_readiness_claim"] is False
    assert report["activation_requested"] is False
    assert report["adapter_tag_published"] is False
    assert report["activation_evidence_sufficient"] is True
    assert len(report["scenario_results"]) == 29
    assert all(r["result"] == "pass" for r in report["scenario_results"])
    assert all(v == 0 for v in report["effect_traps"].values())
    assert report["failures"] == []


def test_overlay_preserves_disabled_targets_and_protected_roles():
    active = load(ROOT / "config/codex-repositories.json")
    staged = load(OVERLAY / "config/codex-repositories.json")
    assert set(active["repositories"]) == set(staged["repositories"])
    for repo in active["repositories"]:
        if repo != TARGET:
            assert staged["repositories"][repo] == active["repositories"][repo]
    assert not (OVERLAY / "config/codex-activation.json").exists()
    enabled = load(ROOT / "config/codex-activation.json")["targets"]
    assert [repo for repo, value in enabled.items() if value] == [TARGET]
    assert staged["repositories"][TARGET]["idempotency"]["reusable_admission_releases"] == ["ai-sdlc-v5.0.0"]
    compat = load(OVERLAY / "config/codex-result-receiver-compatibility.json")
    assert compat["receiver_release"] == "ai-sdlc-v5.0.0"
    assert compat["accepted_admission_releases"] == ["ai-sdlc-v5.0.0"]
    roles = load(OVERLAY / "config/codex-credential-roles.json")["repositories"][TARGET]
    env = roles["environments"]["consulting-playbook-codex"]
    assert "PUBLICATION_READINESS_EVIDENCE" in env["secrets"]
    assert "PUBLICATION_READINESS_EVIDENCE" not in roles["secrets"]
    assert {"PUBLICATION_POLICY_REVISION", "CODEX_AUTHORIZED_CONTROL_PLANE_SHA"} <= env["variables"].keys()
    assert not ({"PUBLICATION_POLICY_REVISION", "CODEX_AUTHORIZED_CONTROL_PLANE_SHA"} & roles["variables"].keys())
    assert "PUBLICATION_CANARY_AUTHORIZATION" not in env["variables"]


def test_structural_overlay_in_temporary_checkout_only():
    # No network, no tags, no write to the real repository, no candidate-ready claim.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for path in (".github/workflows", "config", "contracts", "actions", "tests/fixtures/mvp-v2"):
            shutil.copytree(ROOT / path, root / path)
        for path in ("README.md", "pyproject.toml", "release/release-manifest.json", "release/current-runtime.json"):
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, dest)
        for src in OVERLAY.rglob("*"):
            if src.is_file():
                dest = root / src.relative_to(OVERLAY)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
        assert validate_release.validate(root) == []
        assert "publishable release must declare tag_published true" in validate_release.validate(root, require_publishable=True)
        with patch.object(generate_current_runtime, "ROOT", root):
            assert generate_current_runtime.render() == (root / "release/current-runtime.json").read_text(encoding="utf-8")
    assert load(ROOT / "release/release-manifest.json")["tag"] == "ai-sdlc-v4.0.0"
    assert load(ROOT / "release/release-manifest.json")["tag_published"] is True
