import json
import os
import subprocess

import pytest
from jsonschema import Draft202012Validator


BASE_TASK = {
    "contract_version": "ai-sdlc-contract/v1",
    "task_id": "portfolio-8-attempt-1",
    "source_issue": "Young-Consultations/portfolio-tasks#8",
    "status": "approved",
    "executor": "codex",
    "project": "Publication Output",
    "priority": "p2",
    "task_type": "automation",
    "target_repository": "Young-Consultations/slugger",
    "parallel_safe": False,
    "dependencies": [],
    "risk": "low",
    "scope": "small",
    "instructions": "Make the approved change and open a draft pull request.",
    "created_by": "portfolio-tasks",
}


def run_router(*, github_output=None, **changes):
    task = {**BASE_TASK, **changes}
    env = {key: value for key, value in os.environ.items() if key != "GITHUB_OUTPUT"}
    env["TASK_PAYLOAD"] = json.dumps(task)
    if github_output is not None:
        env["GITHUB_OUTPUT"] = os.fspath(github_output)
    result = subprocess.run(
        ["python3", "scripts/codex_router.py", "validate"], env=env,
        text=True, capture_output=True,
    )
    result.github_output_path = github_output
    return result


def output(result, key):
    prefix = f"{key}="
    for line in result.stdout.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    raise AssertionError(
        f"Missing router output {key!r}.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
        "GitHub output file configured: "
        f"{getattr(result, 'github_output_path', None) is not None}"
    )


def file_outputs(path):
    return dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines())


@pytest.mark.parametrize(
    ("repository", "task_type"),
    [
        ("Young-Consultations/portfolio-tasks", "repository-maintenance"),
        ("Young-Consultations/consulting-playbook", "documentation"),
        ("Young-Consultations/slugger", "automation"),
    ],
)
def test_registered_routes_emit_one_execution_contract(repository, task_type):
    result = run_router(target_repository=repository, task_type=task_type)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output(result, "execution_input"))
    assert set(payload) == {
        "contract_version", "correlation_id", "source_issue", "target_repository",
        "task_type", "project", "priority", "executor", "parallel_safe", "draft_pr_only",
        "instructions", "requested_branch", "concurrency_group", "timeout_minutes",
    }
    assert payload["target_repository"] == repository
    assert payload["project"] == BASE_TASK["project"]


def test_unknown_repository_is_canonical_routing_rejection():
    result = run_router(target_repository="Young-Consultations/unknown")
    assert result.returncode == 1
    assert output(result, "failure_category") == "repository-routing"


def test_disabled_repository_is_rejected(tmp_path):
    path = "config/codex-repositories.json"
    original = open(path, encoding="utf-8").read()
    changed = original.replace('"enabled": true', '"enabled": false', 1)
    try:
        open(path, "w", encoding="utf-8").write(changed)
        result = run_router()
    finally:
        open(path, "w", encoding="utf-8").write(original)
    assert result.returncode == 1
    assert "disabled" in result.stdout


def test_unsupported_task_type_is_rejected():
    result = run_router(task_type="security")
    assert result.returncode == 1
    assert output(result, "failure_category") == "repository-routing"


def test_unresolved_dependency_is_rejected():
    result = run_router(dependencies=["portfolio-7"])
    assert result.returncode == 1
    assert output(result, "failure_category") == "dependency"


def test_unsupported_contract_version_is_rejected():
    result = run_router(contract_version="ai-sdlc-contract/v2")
    assert result.returncode == 1
    assert output(result, "failure_category") == "contract-validation"


def test_duplicate_attempt_has_same_group_and_branch():
    first, second = run_router(), run_router()
    assert output(first, "concurrency_group") == output(second, "concurrency_group")
    assert json.loads(output(first, "execution_input"))["requested_branch"] == json.loads(output(second, "execution_input"))["requested_branch"]


def test_parallel_safe_execution_uses_attempt_boundary():
    first = run_router(parallel_safe=True, task_id="attempt-a")
    second = run_router(parallel_safe=True, task_id="attempt-b")
    assert output(first, "concurrency_group") != output(second, "concurrency_group")
    assert "-parallel-" in output(first, "concurrency_group")


def test_non_parallel_safe_execution_uses_component_boundary():
    first = run_router(task_id="attempt-a")
    second = run_router(task_id="attempt-b")
    assert output(first, "concurrency_group") == output(second, "concurrency_group")
    assert "-serial-publication-output" in output(first, "concurrency_group")
    assert json.loads(output(first, "execution_input"))["concurrency_group"] == output(first, "concurrency_group")


def test_draft_only_is_enforced():
    payload = json.loads(output(run_router(), "execution_input"))
    assert payload["draft_pr_only"] is True


def test_correlation_id_is_propagated():
    result = run_router(task_id="portfolio-8-attempt-9")
    assert output(result, "correlation_id") == "portfolio-8-attempt-9"
    assert json.loads(output(result, "execution_input"))["correlation_id"] == "portfolio-8-attempt-9"


def test_authorization_requires_approved_codex_task():
    assert output(run_router(status="proposed"), "failure_category") == "authorization"
    assert output(run_router(executor="human"), "failure_category") == "authorization"


def test_valid_task_writes_contract_to_github_output_file(tmp_path):
    github_output = tmp_path / "github-output"
    result = run_router(github_output=github_output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "execution_input=" not in result.stdout
    outputs = file_outputs(github_output)
    assert outputs["validation_result"] == "passed"
    assert outputs["target_repository"] == BASE_TASK["target_repository"]
    assert outputs["workflow_ref"]
    assert outputs["concurrency_group"]
    assert outputs["correlation_id"] == BASE_TASK["task_id"]
    execution_input = json.loads(outputs["execution_input"])
    schema = json.loads(open("contracts/execution-input.schema.json", encoding="utf-8").read())
    Draft202012Validator(schema).validate(execution_input)


def test_rejection_writes_canonical_result_to_github_output_file(tmp_path):
    github_output = tmp_path / "github-output"
    result = run_router(
        github_output=github_output,
        target_repository="Young-Consultations/unknown",
    )

    assert result.returncode == 1
    assert "failure_category=" not in result.stdout
    outputs = file_outputs(github_output)
    assert outputs["failure_category"] == "repository-routing"
    assert outputs["validation_result"] == "failed"
    assert json.loads(outputs["execution_result"]) == {
        "correlation_id": BASE_TASK["task_id"],
        "execution_status": "rejected",
        "failure_category": "repository-routing",
        "failure_message": (
            "Repository Young-Consultations/unknown is not registered."
        ),
    }


def test_output_transport_does_not_change_router_semantics(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "step-summary"))
    stdout_result = run_router()
    github_output = tmp_path / "github-output"
    file_result = run_router(github_output=github_output)

    assert stdout_result.returncode == file_result.returncode == 0
    file_values = file_outputs(github_output)
    keys = (
        "execution_input",
        "validation_result",
        "target_repository",
        "workflow_ref",
        "codex_environment",
        "concurrency_group",
        "correlation_id",
        "diagnostic_summary",
    )
    assert {key: output(stdout_result, key) for key in keys} == {
        key: file_values[key] for key in keys
    }


def test_registry_validation_command_passes():
    result = subprocess.run(
        ["python3", "scripts/codex_router.py", "validate-registry"],
        text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_repository_specific_configuration_is_registry_only():
    router = open("scripts/codex_router.py", encoding="utf-8").read()
    for repository in (
        "Young-Consultations/slugger",
        "Young-Consultations/consulting-playbook",
        "Young-Consultations/portfolio-tasks",
    ):
        assert repository not in router
