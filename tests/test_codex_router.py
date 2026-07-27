import json
import os
import subprocess

import pytest


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


def run_router(**changes):
    task = {**BASE_TASK, **changes}
    env = {**os.environ, "TASK_PAYLOAD": json.dumps(task)}
    return subprocess.run(
        ["python3", "scripts/codex_router.py", "validate"], env=env,
        text=True, capture_output=True,
    )


def output(result, key):
    prefix = f"{key}="
    return next(line[len(prefix):] for line in result.stdout.splitlines() if line.startswith(prefix))


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


def test_registry_validation_command_passes():
    result = subprocess.run(
        ["python3", "scripts/codex_router.py", "validate-registry"],
        text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
