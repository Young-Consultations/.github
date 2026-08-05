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


def test_delivery_id_is_required_and_propagated_in_execution_contracts():
    payload = example("execution-input")
    assert payload["delivery_id"] == payload["correlation_id"]
    payload.pop("delivery_id")
    with pytest.raises(ContractValidationError, match=r"\$"):
        validate_execution_input(payload)

    result = example("execution-result")
    assert result["delivery_id"] == result["correlation_id"]
    result.pop("delivery_id")
    with pytest.raises(ContractValidationError, match=r"\$"):
        validate_execution_result(result)


def test_load_contract_version():
    assert load_contract_version() == "ai-sdlc-contract/v2"


def test_packaged_contract_discovery_ignores_prefix_and_working_directory(tmp_path, monkeypatch):
    packaged_contracts = tmp_path / "site-packages/ai_sdlc_contracts/contracts"
    packaged_contracts.mkdir(parents=True)
    (packaged_contracts / "contract-version.txt").write_text("bundled-version\n", encoding="utf-8")
    monkeypatch.setattr(loader, "files", lambda package: packaged_contracts.parent)
    monkeypatch.setattr(loader, "__file__", str(tmp_path / "installed/ai_sdlc_contracts/loader.py"))
    monkeypatch.chdir(tmp_path)

    assert loader.load_contract_version() == "bundled-version"


def test_explicit_contract_directory_override(tmp_path, monkeypatch):
    override = tmp_path / "override"
    override.mkdir()
    (override / "contract-version.txt").write_text("override-version\n", encoding="utf-8")
    monkeypatch.setenv("AI_SDLC_CONTRACT_DIR", str(override))

    assert loader.load_contract_version() == "override-version"


def test_missing_packaged_resources_raise_schema_load_error(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "files", lambda package: tmp_path / "missing-package")
    monkeypatch.setattr(loader, "__file__", str(tmp_path / "installed/ai_sdlc_contracts/loader.py"))
    loader.load_schema.cache_clear()

    with pytest.raises(loader.ContractSchemaLoadError, match="could not be located"):
        loader.load_schema("task")


def test_packaged_contracts_match_canonical_contracts():
    canonical = Path("contracts")
    packaged = Path("src/ai_sdlc_contracts/contracts")
    filenames = {"contract-version.txt", *loader.SCHEMAS.values()}
    for filename in filenames:
        assert (packaged / filename).read_bytes() == (canonical / filename).read_bytes()
        assert (packaged / "v1" / filename).read_bytes() == (canonical / "v1" / filename).read_bytes()


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


def test_cli_invalid_json_preserves_exit_code_two(tmp_path):
    payload = tmp_path / "malformed.json"
    payload.write_text("{", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "ai_sdlc_contracts", "validate-task", str(payload)],
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONPATH="src"),
        check=False,
    )
    assert result.returncode == 2
    assert result.stderr == "error: payload file could not be read as JSON\n"
