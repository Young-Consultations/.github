from __future__ import annotations

import base64
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_target_workflows", ROOT / "scripts/verify_target_workflows.py")
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

FIXTURE = ROOT / "tests/fixtures/target_workflows/portfolio-tasks-codex-execute.yml"
CANONICAL = FIXTURE.read_text(encoding="utf-8")


def workflow(inputs: str) -> str:
    return "on:\n  workflow_dispatch:\n    inputs:\n" + inputs


def canonical_inputs(extra: str = "") -> str:
    return (
        "      execution_input_json: {required: false, type: string}\n"
        "      execution_input_artifact: {required: false, type: string}\n"
        "      execution_input_run_id: {required: false, type: string}\n"
        "      concurrency_group: {required: true, type: string}\n"
        + extra
    )


def registry(tmp_path: Path, entries: dict) -> Path:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"registry_format_version": 1, "repositories": entries}), encoding="utf-8")
    return path


def entry(repo: str = "org/repo", **changes):
    value = {
        "enabled": True,
        "workflow_ref": f"{repo}/.github/workflows/codex-execute.yml@main",
        "contract_version": checker.CANONICAL_VERSION,
        "draft_pr_only": True,
        "max_parallel_tasks": 1,
    }
    value.update(changes)
    return value


def test_canonical_portfolio_tasks_interface():
    assert checker.verify_interface(CANONICAL) == "canonical v2 JSON + artifact transport"


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (workflow("      concurrency_group: {required: true, type: string}\n"), "missing execution_input_json"),
        (workflow("      execution_input_json: {required: false, type: string}\n      execution_input_artifact: {required: false, type: string}\n      execution_input_run_id: {required: false, type: string}\n"), "missing concurrency_group"),
        (workflow("      execution_input_json: {required: false, type: string}\n      execution_input_artifact: {required: false, type: string}\n      execution_input_run_id: {required: false, type: string}\n      concurrency_group: {required: false, type: string}\n"), "required must be true"),
        (workflow("      execution_input_json: {required: false, type: boolean}\n      execution_input_artifact: {required: false, type: string}\n      execution_input_run_id: {required: false, type: string}\n      concurrency_group: {required: true, type: string}\n"), "must have type string"),
        (workflow(canonical_inputs("      extra_required: {required: true, type: string}\n")), "incompatible required"),
    ],
)
def test_incompatible_interfaces(source, message):
    with pytest.raises(checker.CompatibilityError, match=message):
        checker.verify_interface(source)


def test_obsolete_field_by_field_workflow_rejected():
    fields = "".join(f"      {name}: {{required: true, type: string}}\n" for name in checker.CONTRACT_FIELDS)
    source = workflow(canonical_inputs(fields))
    with pytest.raises(checker.CompatibilityError, match="obsolete v1"):
        checker.verify_interface(source)


def test_repository_mismatch(tmp_path):
    path = registry(tmp_path, {"org/repo": entry("other/repo")})
    with pytest.raises(checker.CompatibilityError, match="repository mismatch"):
        checker.load_registry(path)


@pytest.mark.parametrize("reference", ["bad", "org/repo/file.yml@main", "org/repo/.github/workflows/x.yml", "org/repo/.github/workflows/x.yml@main@next"])
def test_malformed_workflow_ref(reference):
    with pytest.raises(checker.CompatibilityError, match="malformed"):
        checker.parse_workflow_ref(reference)


def test_disabled_registry_entry_is_skipped(tmp_path):
    path = registry(tmp_path, {"org/repo": entry(enabled=False)})
    entries = checker.load_registry(path)
    with patch.object(checker, "fetch_workflow") as fetch:
        assert checker.verify_registry(entries, None) == []
        fetch.assert_not_called()


def test_contract_version_mismatch(tmp_path):
    path = registry(tmp_path, {"org/repo": entry(contract_version="ai-sdlc-contract/v1")})
    with pytest.raises(checker.CompatibilityError, match="contract-version mismatch"):
        checker.load_registry(path)


def test_missing_workflow_is_reported_without_network(tmp_path):
    entries = checker.load_registry(registry(tmp_path, {"org/repo": entry()}))
    with patch.object(checker, "fetch_workflow", side_effect=checker.CompatibilityError("workflow is unavailable at registered ref")):
        report = checker.verify_registry(entries, "fake-token")
    assert report[0]["result"] == "fail: workflow is unavailable at registered ref"


def test_network_fetch_is_mocked_for_success(tmp_path):
    entries = checker.load_registry(registry(tmp_path, {"org/repo": entry()}))
    with patch.object(checker, "fetch_workflow", return_value=CANONICAL) as fetch:
        report = checker.verify_registry(entries, "fake-token")
    fetch.assert_called_once_with("org/repo", ".github/workflows/codex-execute.yml", "main", "fake-token")
    assert report[0]["result"] == "pass (warning: movable ref)"


def test_fetch_workflow_accepts_line_wrapped_contents_api_payload():
    content = base64.encodebytes(CANONICAL.encode("utf-8")).decode("ascii")
    response = io.BytesIO(json.dumps({"content": content}).encode("utf-8"))

    with patch.object(checker.urllib.request, "urlopen", return_value=response):
        assert checker.fetch_workflow(
            "org/repo", ".github/workflows/codex-execute.yml", "fixed-ref", "fake-token"
        ) == CANONICAL


def test_main_keeps_diagnostics_and_results_visible_with_actions_summary(tmp_path, capsys):
    summary = tmp_path / "summary.md"
    report = tmp_path / "report.json"
    registry_path = registry(tmp_path, {"org/repo": entry()})

    with patch.dict(checker.os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}):
        assert checker.main([
            "--fixtures-only", "--registry", str(registry_path), "--report", str(report)
        ]) == 0

    captured = capsys.readouterr()
    assert "AI-SDLC target compatibility" in captured.out
    assert "loaded 1 registry entries" in captured.err
    assert "checked=1, failed=0" in captured.err
    assert "AI-SDLC target compatibility" in summary.read_text(encoding="utf-8")


def test_fetch_failure_reports_http_status_and_url():
    error = checker.urllib.error.HTTPError(
        "https://api.github.test/workflow", 404, "Not Found", {}, None
    )

    with patch.object(checker.urllib.request, "urlopen", side_effect=error), pytest.raises(
        checker.CompatibilityError, match=r"HTTP 404: Not Found"
    ) as raised:
        checker.fetch_workflow("org/repo", ".github/workflows/codex-execute.yml", "missing")

    assert "api.github.com/repos/org/repo/contents/" in str(raised.value)


def test_all_canonical_router_inputs_must_be_declared():
    source = workflow("      execution_input_json: {required: false, type: string}\n      concurrency_group: {required: true, type: string}\n")
    with pytest.raises(checker.CompatibilityError, match="missing execution_input_artifact"):
        checker.verify_interface(source)


def test_incompatible_required_input_is_rejected():
    source = workflow(
        "      execution_input_json: {required: false, type: string}\n"
        "      execution_input_artifact: {required: false, type: string}\n"
        "      execution_input_run_id: {required: false, type: string}\n"
        "      concurrency_group: {required: true, type: string}\n"
        "      extra_required: {required: true, type: string}\n"
    )
    with pytest.raises(checker.CompatibilityError, match="incompatible required"):
        checker.verify_interface(source)


def test_issue_to_codex_cannot_be_registered(tmp_path):
    path = registry(tmp_path, {"org/repo": entry(workflow_ref="org/repo/.github/workflows/issue-to-codex.yml@main")})
    with pytest.raises(checker.CompatibilityError, match="obsolete workflow_ref"):
        checker.load_registry(path)


def test_draft_only_must_remain_true(tmp_path):
    path = registry(tmp_path, {"org/repo": entry(draft_pr_only=False)})
    with pytest.raises(checker.CompatibilityError, match="draft-only"):
        checker.load_registry(path)


def test_deterministic_concurrency_policy_is_required(tmp_path):
    path = registry(tmp_path, {"org/repo": entry(max_parallel_tasks=0)})
    with pytest.raises(checker.CompatibilityError, match="deterministic concurrency"):
        checker.load_registry(path)


def test_duplicate_repository_registration_is_rejected(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text(
        '{"registry_format_version":1,"repositories":{"org/repo":'
        + json.dumps(entry())
        + ',"org/repo":'
        + json.dumps(entry())
        + '}}',
        encoding="utf-8",
    )
    with pytest.raises(checker.CompatibilityError, match="duplicate JSON key"):
        checker.load_registry(path)


def test_one_incompatible_target_does_not_block_unrelated_target(tmp_path):
    entries = checker.load_registry(registry(tmp_path, {"org/good": entry("org/good"), "org/bad": entry("org/bad")}))
    def fake_fetch(repo, path, ref, token):
        if repo == "org/bad":
            return workflow("      execution_input_json: {required: false, type: string}\n")
        return CANONICAL
    with patch.object(checker, "fetch_workflow", side_effect=fake_fetch):
        report = checker.verify_registry(entries, None)
    assert report[0]["result"] == "pass (warning: movable ref)"
    assert report[1]["result"].startswith("fail:")


def test_api_diagnostics_are_sanitized():
    error = checker.urllib.error.URLError("Authorization:Bearer ghp_secret123 token=ghp_secret123")
    with patch.object(checker.urllib.request, "urlopen", side_effect=error), pytest.raises(checker.CompatibilityError) as raised:
        checker.fetch_workflow("org/repo", ".github/workflows/codex-execute.yml", "main", "ghp_secret123")
    message = str(raised.value)
    assert "ghp_secret123" not in message
    assert "Authorization" not in message or "[redacted]" in message


def test_migrated_target_entries_use_v2_and_expected_paths():
    entries = checker.load_registry(ROOT / "config/codex-repositories.json")
    assert entries["Young-Consultations/slugger"]["contract_version"] == checker.CANONICAL_VERSION
    assert entries["Young-Consultations/consulting-playbook"]["contract_version"] == checker.CANONICAL_VERSION
    assert entries["Young-Consultations/slugger"]["workflow_ref"] == "Young-Consultations/slugger/.github/workflows/codex-execute.yml@main"
    assert entries["Young-Consultations/consulting-playbook"]["workflow_ref"] == "Young-Consultations/consulting-playbook/.github/workflows/codex-execute.yml@main"
