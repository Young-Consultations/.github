import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ai_sdlc_contracts import (
    ExecutionMode,
    TaskContractBuildError,
    build_task_contract_from_issue,
    validate_task,
)


FIXTURE = Path("tests/fixtures/issue-42.json")
SOURCE = "Young-Consultations/portfolio-tasks"


def issue():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("mode", [ExecutionMode.IMPLEMENT, ExecutionMode.VERIFY])
def test_builds_valid_approved_documentation_contract(mode):
    contract = build_task_contract_from_issue(
        source_repository=SOURCE, issue=issue(), execution_mode=mode
    )
    validate_task(contract)
    assert contract["source_issue"] == f"{SOURCE}#42"
    assert contract["target_repository"] == "Young-Consultations/consulting-playbook"
    assert contract["task_type"] == "documentation"
    assert contract["status"] == "approved"
    assert "Acceptance Criteria:" in contract["instructions"]
    assert "Definition Of Done:" in contract["instructions"]


def test_preserves_complete_structured_issue_intent_in_order_without_truncation():
    payload = issue()
    sections = [
        ("Instructions", "Implement the complete requested change."),
        ("Objective", "Preserve the entire issue specification."),
        ("Current Behavior", "The final structured sections are silently dropped."),
        ("Required Behavior", "Forward every section to the executor."),
        ("In-Scope Files", "- src/ai_sdlc_contracts/builder.py"),
        ("Out-of-Scope Files", "- contracts/task-contract.schema.json"),
        (
            "Architectural Constraints",
            "Keep the schema, payload, routing, and workflow interfaces unchanged.",
        ),
        ("Constraints", "Do not flatten the specification."),
        ("Acceptance Criteria", "All structured intent reaches Codex."),
        ("Testing Requirements", "Run the complete validation suite."),
        (
            "Definition of Done",
            "The final sentinel text remains present: END-OF-ISSUE-49.",
        ),
    ]
    payload["body"] = "\n\n".join(
        [
            "## Target repository\nYoung-Consultations/consulting-playbook",
            "## Task type\nbug-fix",
            "## Execution status\napproved",
            *(f"## {heading}\n{content}" for heading, content in sections),
        ]
    )

    contract = build_task_contract_from_issue(
        source_repository=SOURCE,
        issue=payload,
        execution_mode=ExecutionMode.IMPLEMENT,
    )
    expected = "\n\n".join(
        f"## {heading.title()}\n{content}" for heading, content in sections
    )
    assert contract["instructions"] == expected
    assert contract["instructions"].endswith("END-OF-ISSUE-49.")


def test_legacy_issue_instruction_assembly_is_unchanged():
    payload = issue()
    contract = build_task_contract_from_issue(
        source_repository=SOURCE,
        issue=payload,
        execution_mode=ExecutionMode.IMPLEMENT,
    )
    assert contract["instructions"] == (
        "Document the approved consulting workflow and open a draft pull request.\n\n"
        "Constraints:\n- Do not change runtime behavior.\n\n"
        "Acceptance Criteria:\n- The guide contains a complete example.\n\n"
        "Testing Requirements:\n- Run the documentation checks.\n\n"
        "Definition Of Done:\n- A focused draft pull request is open."
    )


@pytest.mark.parametrize(
    ("heading", "message"),
    [("Target repository", "target repository"), ("Task type", "task type")],
)
def test_missing_required_field(heading, message):
    payload = issue()
    payload["body"] = payload["body"].replace(
        f"## {heading}\n", f"## Removed {heading}\n"
    )
    with pytest.raises(TaskContractBuildError, match=message):
        build_task_contract_from_issue(
            source_repository=SOURCE,
            issue=payload,
            execution_mode=ExecutionMode.IMPLEMENT,
        )


@pytest.mark.parametrize("heading", ["Execution status", "Status"])
def test_missing_execution_status_is_not_implicitly_approved(heading):
    payload = issue()
    payload["body"] = payload["body"].replace(
        "## Execution status\napproved", f"## {heading}\n"
    )
    with pytest.raises(TaskContractBuildError, match="execution status or status"):
        build_task_contract_from_issue(
            source_repository=SOURCE,
            issue=payload,
            execution_mode=ExecutionMode.IMPLEMENT,
        )


def test_status_alias_is_accepted_when_explicit():
    payload = issue()
    payload["body"] = payload["body"].replace(
        "## Execution status\napproved", "## Status\nqueued"
    )
    contract = build_task_contract_from_issue(
        source_repository=SOURCE,
        issue=payload,
        execution_mode=ExecutionMode.IMPLEMENT,
    )
    assert contract["status"] == "queued"


def test_unsupported_task_type():
    payload = issue()
    payload["body"] = payload["body"].replace(
        "## Task type\ndocumentation", "## Task type\nresearch"
    )
    with pytest.raises(TaskContractBuildError, match="unsupported task type"):
        build_task_contract_from_issue(
            source_repository=SOURCE,
            issue=payload,
            execution_mode=ExecutionMode.IMPLEMENT,
        )


@pytest.mark.parametrize("body", [None, "", {"unexpected": "object"}])
def test_missing_or_malformed_body(body):
    payload = issue()
    payload["body"] = body
    with pytest.raises(TaskContractBuildError, match="issue body"):
        build_task_contract_from_issue(
            source_repository=SOURCE,
            issue=payload,
            execution_mode=ExecutionMode.IMPLEMENT,
        )


@pytest.mark.parametrize(
    "repository", ["portfolio-tasks", "owner/", "owner/repo/extra"]
)
def test_invalid_source_repository(repository):
    with pytest.raises(TaskContractBuildError, match="source repository"):
        build_task_contract_from_issue(
            source_repository=repository,
            issue=issue(),
            execution_mode=ExecutionMode.IMPLEMENT,
        )


def test_invalid_execution_mode_for_python_api():
    with pytest.raises(TaskContractBuildError, match="execution mode"):
        build_task_contract_from_issue(
            source_repository=SOURCE, issue=issue(), execution_mode="deploy"
        )


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "ai_sdlc_contracts", *map(str, args)],
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONPATH="src"),
        check=False,
    )


def test_cli_build_is_deterministic_and_both_validation_commands_accept_it(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    command = (
        "build-task-contract",
        "--source-repository",
        SOURCE,
        "--issue-json",
        FIXTURE,
        "--execution-mode",
        "implement",
    )
    assert run_cli(*command, "--output", first).returncode == 0
    assert run_cli(*command, "--output", second).returncode == 0
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes().endswith(b"\n")
    assert run_cli("validate-task", first).stdout == "valid\n"
    assert run_cli("validate-task-contract", first).stdout == "valid\n"


def test_cli_rejects_invalid_issue_json_without_echoing_payload(tmp_path):
    secret = "PRIVATE-ISSUE-CONTENT"
    malformed = tmp_path / "issue.json"
    malformed.write_text('{"body": "' + secret, encoding="utf-8")
    result = run_cli(
        "build-task-contract",
        "--source-repository",
        SOURCE,
        "--issue-json",
        malformed,
        "--execution-mode",
        "implement",
        "--output",
        tmp_path / "output.json",
    )
    assert result.returncode != 0
    assert "could not be read as JSON" in result.stderr
    assert secret not in result.stderr


def test_cli_rejects_non_object_issue_without_echoing_payload(tmp_path):
    payload = copy.deepcopy(issue())
    secret = "PRIVATE-ISSUE-CONTENT"
    payload["body"] += secret
    source = tmp_path / "issue.json"
    source.write_text(json.dumps([payload]), encoding="utf-8")
    result = run_cli(
        "build-task-contract",
        "--source-repository",
        SOURCE,
        "--issue-json",
        source,
        "--execution-mode",
        "implement",
        "--output",
        tmp_path / "output.json",
    )
    assert result.returncode != 0
    assert "GitHub issue object" in result.stderr
    assert secret not in result.stderr


def test_cli_rejects_invalid_execution_mode(tmp_path):
    result = run_cli(
        "build-task-contract",
        "--source-repository",
        SOURCE,
        "--issue-json",
        FIXTURE,
        "--execution-mode",
        "deploy",
        "--output",
        tmp_path / "output.json",
    )
    assert result.returncode != 0
    assert "invalid choice" in result.stderr
