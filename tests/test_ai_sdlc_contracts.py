import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ai_sdlc_contracts import (
    ContractValidationError,
    UnsupportedContractVersionError,
    loader,
    load_contract_version,
    validate_execution_input,
    validate_execution_result,
    validate_task,
)
from ai_sdlc_contracts.normalization import normalize_payload


EXAMPLES = Path("contracts/examples")


def example(name):
    return json.loads((EXAMPLES / f"valid-{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("name", "validator"),
    [
        ("task", validate_task),
        ("execution-input", validate_execution_input),
        ("execution-result", validate_execution_result),
    ],
)
def test_valid_payloads(name, validator):
    assert validator(example(name)) is None


def test_load_contract_version():
    assert load_contract_version() == "ai-sdlc-contract/v1"


def test_installed_contract_discovery_ignores_working_directory(tmp_path, monkeypatch):
    installed_package = tmp_path / "prefix/lib/python3.9/site-packages/ai_sdlc_contracts"
    installed_package.mkdir(parents=True)
    bundled_contracts = tmp_path / "prefix/share/ai-sdlc-contracts/contracts"
    bundled_contracts.mkdir(parents=True)
    (bundled_contracts / "contract-version.txt").write_text("bundled-version\n", encoding="utf-8")

    unrelated_contracts = tmp_path / "project/contracts"
    unrelated_contracts.mkdir(parents=True)
    (unrelated_contracts / "contract-version.txt").write_text("unrelated-version\n", encoding="utf-8")

    monkeypatch.setattr(loader, "__file__", str(installed_package / "loader.py"))
    monkeypatch.setattr(loader.sys, "prefix", str(tmp_path / "prefix"))
    monkeypatch.chdir(tmp_path / "project")

    assert loader.load_contract_version() == "bundled-version"


@pytest.mark.parametrize(
    ("name", "validator"),
    [
        ("task", validate_task),
        ("execution-input", validate_execution_input),
        ("execution-result", validate_execution_result),
    ],
)
def test_unsupported_version_has_explicit_error(name, validator):
    payload = example(name)
    payload["contract_version"] = "ai-sdlc-contract/v999"
    with pytest.raises(UnsupportedContractVersionError, match=r"\$\.contract_version"):
        validator(payload)


@pytest.mark.parametrize("field,value", [("priority", "urgent"), ("task_type", "repository governance")])
def test_invalid_and_ambiguous_enum_values_are_rejected(field, value):
    payload = example("task")
    payload[field] = value
    with pytest.raises(ContractValidationError, match=rf"\$\.{field}"):
        validate_task(payload)


def test_unknown_field_path_is_reported():
    payload = example("task")
    payload["unknown_secret"] = "do not expose this value"
    with pytest.raises(ContractValidationError, match=r"\$\.unknown_secret"):
        validate_task(payload)


@pytest.mark.parametrize("repository", ["repo", "owner/", "owner/repo/extra"])
def test_repository_validation(repository):
    payload = example("task")
    payload["target_repository"] = repository
    with pytest.raises(ContractValidationError, match=r"\$\.target_repository"):
        validate_task(payload)


@pytest.mark.parametrize("issue", ["repo#1", "owner/repo", "owner/repo#0"])
def test_issue_reference_validation(issue):
    payload = example("execution-input")
    payload["source_issue"] = issue
    with pytest.raises(ContractValidationError, match=r"\$\.source_issue"):
        validate_execution_input(payload)


def test_safe_legacy_values_are_normalized_without_mutation():
    payload = example("task")
    payload.update(priority="P1", executor="Codex", status="Draft PR")
    original = copy.deepcopy(payload)
    validate_task(payload)
    assert payload == original


def test_explicit_task_type_migration_can_be_configured():
    payload = example("task")
    payload["task_type"] = "repository governance"
    normalized = normalize_payload(
        payload,
        migration_mappings={"task_type": {"repository governance": "repository-maintenance"}},
    )
    validate_task(normalized)


def test_diagnostics_do_not_include_sensitive_values():
    payload = example("task")
    secret = "SUPER-SECRET-INSTRUCTION"
    payload["instructions"] = secret * 5000
    with pytest.raises(ContractValidationError) as caught:
        validate_task(payload)
    assert secret not in str(caught.value)
    assert "$.instructions" in str(caught.value)


@pytest.mark.parametrize(
    "command", ["validate-task", "validate-input", "validate-result"]
)
def test_cli_accepts_valid_examples(command):
    suffix = {"validate-task": "task", "validate-input": "execution-input", "validate-result": "execution-result"}[command]
    env = dict(os.environ, PYTHONPATH="src")
    result = subprocess.run(
        [sys.executable, "-m", "ai_sdlc_contracts", command, str(EXAMPLES / f"valid-{suffix}.json")],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == "valid\n"
