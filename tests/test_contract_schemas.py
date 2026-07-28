import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError


CONTRACTS = Path("contracts")
CASES = {
    "task": ("task-contract.schema.json", "valid-task.json"),
    "input": ("execution-input.schema.json", "valid-execution-input.json"),
    "result": ("execution-result.schema.json", "valid-execution-result.json"),
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def case(name):
    schema_name, example_name = CASES[name]
    schema = load_json(CONTRACTS / schema_name)
    instance = load_json(CONTRACTS / "examples" / example_name)
    return Draft202012Validator(schema, format_checker=FormatChecker()), instance


def test_version_file_matches_every_schema():
    version = (CONTRACTS / "contract-version.txt").read_text(encoding="utf-8").strip()
    for schema_name, _ in CASES.values():
        assert load_json(CONTRACTS / schema_name)["properties"]["contract_version"]["const"] == version


@pytest.mark.parametrize("name", CASES)
def test_schemas_are_valid_and_examples_pass(name):
    validator, instance = case(name)
    validator.check_schema(validator.schema)
    validator.validate(instance)


@pytest.mark.parametrize("name", CASES)
def test_missing_required_fields_fail(name):
    validator, instance = case(name)
    instance.pop("contract_version")
    with pytest.raises(ValidationError):
        validator.validate(instance)


@pytest.mark.parametrize(
    ("name", "field", "value"),
    [("task", "status", "ready"), ("input", "priority", "urgent"), ("result", "execution_status", "complete")],
)
def test_unsupported_enum_values_fail(name, field, value):
    validator, instance = case(name)
    instance[field] = value
    with pytest.raises(ValidationError):
        validator.validate(instance)


@pytest.mark.parametrize("name", CASES)
def test_unknown_fields_fail(name):
    validator, instance = case(name)
    instance["future_extension"] = True
    with pytest.raises(ValidationError):
        validator.validate(instance)


@pytest.mark.parametrize("name", CASES)
def test_mismatched_contract_versions_fail(name):
    validator, instance = case(name)
    instance["contract_version"] = "ai-sdlc-contract/v2"
    with pytest.raises(ValidationError):
        validator.validate(instance)


def test_codex_input_cannot_disable_draft_pr_only():
    validator, instance = case("input")
    instance["draft_pr_only"] = False
    with pytest.raises(ValidationError):
        validator.validate(instance)


def test_execution_input_requires_codex_executor():
    validator, instance = case("input")
    instance["executor"] = "human"
    with pytest.raises(ValidationError):
        validator.validate(instance)


@pytest.mark.parametrize("mode", ["verify", "implement"])
def test_execution_input_accepts_canonical_execution_modes(mode):
    validator, instance = case("input")
    instance["execution_mode"] = mode
    validator.validate(instance)


def test_execution_input_rejects_invalid_or_missing_execution_mode():
    validator, instance = case("input")
    instance["execution_mode"] = "dry-run"
    with pytest.raises(ValidationError):
        validator.validate(instance)
    instance.pop("execution_mode")
    with pytest.raises(ValidationError):
        validator.validate(instance)


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("repository", ["missing-owner", "/repo", "owner/", "owner/repo/extra", "owner repo/name"])
def test_malformed_repository_names_fail(name, repository):
    validator, instance = case(name)
    instance["target_repository"] = repository
    with pytest.raises(ValidationError):
        validator.validate(instance)


@pytest.mark.parametrize("name", ["task", "input"])
@pytest.mark.parametrize("issue", ["portfolio-tasks#12", "owner/repo", "owner/repo#0", "owner/repo#abc", "owner/repo#1/extra"])
def test_malformed_issue_references_fail(name, issue):
    validator, instance = case(name)
    instance["source_issue"] = issue
    with pytest.raises(ValidationError):
        validator.validate(instance)


def test_draft_pr_result_requires_pr_details():
    validator, instance = case("result")
    for field in ("branch_name", "pull_request_url"):
        invalid = copy.deepcopy(instance)
        invalid[field] = None
        with pytest.raises(ValidationError):
            validator.validate(invalid)


def test_failure_category_requires_message():
    validator, instance = case("result")
    instance["execution_status"] = "failed"
    instance["failure_category"] = "tests"
    with pytest.raises(ValidationError):
        validator.validate(instance)


def test_verified_result_requires_passed_checks_and_no_publication():
    validator, instance = case("result")
    instance = load_json(
        CONTRACTS / "examples" / "valid-verification-result.json"
    )
    validator.validate(instance)

    for field, value in (
        ("branch_name", "codex/not-allowed"),
        ("pull_request_url", "https://github.com/example/repo/pull/1"),
        ("validation_result", "failed"),
        ("test_result", "not-run"),
    ):
        invalid = copy.deepcopy(instance)
        invalid[field] = value
        with pytest.raises(ValidationError):
            validator.validate(invalid)
