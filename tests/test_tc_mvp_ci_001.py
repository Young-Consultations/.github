import copy
import json

from scripts import run_tc_mvp_ci_001 as harness


def test_checked_in_report_matches_current_non_recursive_pin():
    pin = json.loads(harness.PIN_PATH.read_text(encoding="utf-8"))
    report = json.loads(
        (harness.ROOT / ".ai-sdlc/conformance/tc-mvp-ci-001.json").read_text(encoding="utf-8")
    )

    assert pin["adapter_revision"] == harness.pin_revision(pin)
    assert report["adapter_revision"] == pin["adapter_revision"]
    assert report["compatibility_sha"] == pin["compatibility_sha"]
    assert report["activation_evidence_sufficient"] is True
    assert report["adapter_tag_published"] is False
    assert report["receiver_live_verification"] == "pending-ai-sdlc-v2.3.1-tag"
    assert report["failures"] == []
    assert not any(report["effect_traps"].values())


def test_pinned_oracle_writes_real_adapter_zero_effect_report(tmp_path, monkeypatch):
    pin = json.loads(harness.PIN_PATH.read_text(encoding="utf-8"))
    monkeypatch.setattr(harness, "_tree_identities", lambda commit, paths: pin["compatibility_files"])
    report_path = tmp_path / "report.json"

    assert harness.run(report_path) == []
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["compatibility_sha"] == "e27b8a541afbd27b4be5606a19ffa43637ad312a"
    assert report["production_readiness_claim"] is False
    assert report["activation_requested"] is False
    assert report["activation_evidence_sufficient"] is True
    assert report["adapter_tag_published"] is False
    assert report["receiver_live_verification"] == "pending-ai-sdlc-v2.3.1-tag"
    assert report["activation_evidence_reason"] == (
        "complete shared oracle executed through the repository adapter with deterministic effect traps"
    )
    assert report["failures"] == []
    assert all(item["result"] == "pass" for item in report["scenario_results"])
    by_id = {item["id"]: item for item in report["scenario_results"]}
    assert by_id["valid-verify"]["adapter_invoked"] is True
    assert by_id["create-race-ambiguous"]["adapter_invoked"] is True
    assert by_id["disabled-target"]["adapter_invoked"] is False
    assert set(report["effect_traps"]) == set(harness.TRAPPED_EFFECTS)
    assert not any(report["effect_traps"].values())


def test_pin_revision_is_non_recursive():
    pin = json.loads(harness.PIN_PATH.read_text(encoding="utf-8"))
    expected = harness.pin_revision(pin)
    pin["adapter_revision"] = "sha256:" + "f" * 64
    assert harness.pin_revision(pin) == expected


def test_pin_requires_executed_adapter():
    pin = json.loads(harness.PIN_PATH.read_text(encoding="utf-8"))
    del pin["target_files"]["scripts/codex_target_adapter.py"]
    pin["adapter_revision"] = harness.pin_revision(pin)

    assert harness.validate_pin(pin) == ["compatibility pin has the wrong target file set"]


def test_pin_rejects_changed_target_file(tmp_path, monkeypatch):
    repository_root = harness.ROOT
    pin = json.loads(harness.PIN_PATH.read_text(encoding="utf-8"))
    for relative in {*pin["compatibility_files"], *pin["target_files"]}:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((repository_root / relative).read_bytes())
    changed = "scripts/codex_target_adapter.py"
    (tmp_path / changed).write_text("# changed\n", encoding="utf-8")
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "_tree_identities", lambda commit, paths: pin["compatibility_files"])

    assert harness.validate_pin(pin) == [f"pinned target file is incompatible: {changed}"]


def test_pin_rejects_identity_not_present_at_compatibility_revision(tmp_path, monkeypatch):
    repository_root = harness.ROOT
    pin = copy.deepcopy(json.loads(harness.PIN_PATH.read_text(encoding="utf-8")))
    for relative in {*pin["compatibility_files"], *pin["target_files"]}:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((repository_root / relative).read_bytes())
    relative = "tests/fixtures/mvp-v2/expected-results.json"
    changed = b"{}\n"
    (tmp_path / relative).write_bytes(changed)
    old_identities = dict(pin["compatibility_files"])
    pin["compatibility_files"][relative] = harness.git_blob_sha1(changed)
    pin["adapter_revision"] = harness.pin_revision(pin)
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "_tree_identities", lambda commit, paths: old_identities)

    assert harness.validate_pin(pin) == [f"pinned identity differs from compatibility revision: {relative}"]
