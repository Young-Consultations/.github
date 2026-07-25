import os
import subprocess

import pytest

BASE_ENV = {
    "SOURCE_ISSUE": "Young-Consultations/portfolio-tasks#8",
    "TARGET_REPOSITORY": "Young-Consultations/slugger",
    "TASK_TYPE": "automation",
    "PROJECT_COMPONENT": "Publication Output",
    "PRIORITY": "normal",
    "PARALLEL_SAFE": "false",
    "DEPENDENCY_STATUS": "satisfied",
    "APPROVED_EXECUTION_METADATA": '{"approved": true, "approved_by": "portfolio-tasks", "approval_id": "8"}',
}


def run_router(env):
    merged = os.environ.copy()
    merged.update(BASE_ENV)
    merged.update(env)
    return subprocess.run(["python3", "scripts/codex_router.py", "validate"], env=merged, text=True, capture_output=True)


def test_registered_slugger_task_validates():
    result = run_router({})
    assert result.returncode == 0, result.stderr
    assert "validation_result=passed" in result.stdout
    assert "target_repository=Young-Consultations/slugger" in result.stdout


def test_consulting_playbook_reaches_boundary():
    result = run_router({"TARGET_REPOSITORY": "Young-Consultations/consulting-playbook", "TASK_TYPE": "documentation"})
    assert result.returncode == 0, result.stderr
    assert "consulting-playbook" in result.stdout
    assert "validation_result=passed" in result.stdout


@pytest.mark.parametrize(
    "task_type",
    ["automation", "backlog-governance", "ci-cd", "documentation", "repository-maintenance"],
)
def test_portfolio_tasks_permitted_task_types_validate(task_type):
    result = run_router({"TARGET_REPOSITORY": "Young-Consultations/portfolio-tasks", "TASK_TYPE": task_type})
    assert result.returncode == 0, result.stderr
    assert "target_repository=Young-Consultations/portfolio-tasks" in result.stdout
    assert "codex_environment=portfolio-tasks-codex-production" in result.stdout
    assert "workflow_ref=Young-Consultations/portfolio-tasks/.github/workflows/codex-execute.yml@main" in result.stdout


def test_portfolio_tasks_rejects_unpermitted_task_type():
    result = run_router({"TARGET_REPOSITORY": "Young-Consultations/portfolio-tasks", "TASK_TYPE": "feature"})
    assert result.returncode != 0
    assert "not allowed" in result.stdout or "not allowed" in result.stderr


def test_unknown_repository_fails_before_execution():
    result = run_router({"TARGET_REPOSITORY": "Young-Consultations/unknown"})
    assert result.returncode != 0
    assert "not registered" in result.stdout or "not registered" in result.stderr


def test_disabled_repository_fails(tmp_path):
    registry = tmp_path / "registry.yml"
    original = open("config/codex-repositories.json", encoding="utf-8").read()
    registry.write_text(original.replace('"enabled": true', '"enabled": false', 1), encoding="utf-8")
    # Simulate by temporarily replacing registry in-place; restore immediately after.
    os.replace("config/codex-repositories.json", "config/codex-repositories.json.bak")
    os.replace(registry, "config/codex-repositories.json")
    try:
        result = run_router({})
    finally:
        os.replace("config/codex-repositories.json.bak", "config/codex-repositories.json")
    assert result.returncode != 0
    assert "disabled" in result.stdout or "disabled" in result.stderr


def test_conflicting_tasks_share_deterministic_concurrency_group():
    first = run_router({"PROJECT_COMPONENT": "API Client", "PARALLEL_SAFE": "false"})
    second = run_router({"PROJECT_COMPONENT": "API Client", "PARALLEL_SAFE": "false"})
    assert first.returncode == second.returncode == 0
    group_line = [line for line in first.stdout.splitlines() if line.startswith("concurrency_group=")][0]
    assert group_line in second.stdout
    assert group_line.endswith("api-client")


def test_parallel_safe_tasks_get_unique_group():
    first = run_router({"PROJECT_COMPONENT": "API Client", "PARALLEL_SAFE": "true"})
    second = run_router({"PROJECT_COMPONENT": "API Client", "PARALLEL_SAFE": "true"})
    assert first.returncode == second.returncode == 0
    first_group = [line for line in first.stdout.splitlines() if line.startswith("concurrency_group=")][0]
    second_group = [line for line in second.stdout.splitlines() if line.startswith("concurrency_group=")][0]
    assert first_group != second_group


def test_requires_approved_metadata():
    result = run_router({"APPROVED_EXECUTION_METADATA": '{"approved": false}'})
    assert result.returncode != 0
    assert "approved" in result.stdout or "approved" in result.stderr
