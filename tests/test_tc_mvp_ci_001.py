import json

from scripts import run_tc_mvp_ci_001 as harness


def test_pinned_oracle_writes_zero_effect_report(tmp_path):
    report_path = tmp_path / "report.json"
    assert harness.run(report_path) == []
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["compatibility_sha"] == "c6090e5bbadcc2102a1cb91875466e9decdada1e"
    assert report["production_readiness_claim"] is False
    assert report["activation_requested"] is False
    assert report["activation_evidence_sufficient"] is False
    assert report["activation_evidence_reason"] == "shared fixtures were not executed through the repository adapter"
    assert report["failures"] == []
    assert report["scenario_results"]
    assert all(item["result"] == "pass" for item in report["scenario_results"])
    assert set(report["effect_traps"]) == set(harness.TRAPPED_EFFECTS)
    assert not any(report["effect_traps"].values())


def test_pin_rejects_incompatible_expected_behavior(tmp_path, monkeypatch):
    relative = "tests/fixtures/mvp-v2/expected-results.json"
    pin = json.loads(harness.PIN_PATH.read_text(encoding="utf-8"))
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    (tmp_path / relative).parent.mkdir(parents=True)
    (tmp_path / relative).write_text("{}\n", encoding="utf-8")
    pin["files"] = {relative: pin["files"][relative]}
    assert harness.validate_pin(pin) == [f"pinned file is incompatible: {relative}"]


def test_pin_rejects_identity_changed_with_local_file(tmp_path, monkeypatch):
    relative = "tests/fixtures/mvp-v2/expected-results.json"
    pin = json.loads(harness.PIN_PATH.read_text(encoding="utf-8"))
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    (tmp_path / relative).parent.mkdir(parents=True)
    changed = b"{}\n"
    (tmp_path / relative).write_bytes(changed)
    pin["files"] = {relative: harness.git_blob_sha1(changed)}

    assert harness.validate_pin(pin) == [f"pinned identity differs from compatibility revision: {relative}"]
