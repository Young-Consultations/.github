from __future__ import annotations

import importlib.util
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


def registry(tmp_path: Path, entries: dict) -> Path:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"repositories": entries}), encoding="utf-8")
    return path


def entry(repo: str = "org/repo", **changes):
    value = {
        "enabled": True,
        "workflow_ref": f"{repo}/.github/workflows/codex-execute.yml@main",
        "contract_version": checker.CANONICAL_VERSION,
    }
    value.update(changes)
    return value


def test_canonical_portfolio_tasks_interface():
    assert checker.verify_interface(CANONICAL) == "direct JSON + optional artifact"


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (workflow("      concurrency_group: {required: true, type: string}\n"), "missing execution_input_json"),
        (workflow("      execution_input_json: {required: false, type: string}\n"), "missing concurrency_group"),
        (workflow("      execution_input_json: {required: false, type: string}\n      concurrency_group: {required: false, type: string}\n"), "required must be true"),
        (workflow("      execution_input_json: {required: false, type: boolean}\n      concurrency_group: {required: true, type: string}\n"), "must have type string"),
        (workflow("      execution_input_json: {required: false, type: string}\n      concurrency_group: {required: true, type: string}\n      correlation_id: {required: true, type: string}\n"), "must not be required separately"),
    ],
)
def test_incompatible_interfaces(source, message):
    with pytest.raises(checker.CompatibilityError, match=message):
        checker.verify_interface(source)


def test_obsolete_field_by_field_workflow_rejected():
    fields = "".join(f"      {name}: {{required: true, type: string}}\n" for name in checker.CONTRACT_FIELDS)
    source = workflow("      execution_input_json: {required: false, type: string}\n      concurrency_group: {required: true, type: string}\n" + fields)
    with pytest.raises(checker.CompatibilityError, match="contract fields"):
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
    path = registry(tmp_path, {"org/repo": entry(enabled=False, workflow_ref="not parsed")})
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
