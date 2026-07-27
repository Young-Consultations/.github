import json
from pathlib import Path


def test_registry_json_syntax_and_required_fields():
    data = json.loads(Path("config/codex-repositories.json").read_text(encoding="utf-8"))
    repos = data["repositories"]
    assert "Young-Consultations/slugger" in repos
    assert "Young-Consultations/consulting-playbook" in repos
    assert "Young-Consultations/portfolio-tasks" in repos
    for name, entry in repos.items():
        assert isinstance(entry["enabled"], bool), name
        assert entry["allowed_task_types"], name
        assert entry["codex_environment"], name
        assert entry["max_parallel_tasks"] >= 1, name
        assert entry["draft_pr_only"] is True, name
        assert entry["workflow_ref"].startswith(f"{name}/.github/workflows/"), name
        assert entry["contract_version"] == "ai-sdlc-contract/v1", name


def test_portfolio_tasks_registration_contract():
    data = json.loads(Path("config/codex-repositories.json").read_text(encoding="utf-8"))
    entry = data["repositories"]["Young-Consultations/portfolio-tasks"]
    assert entry["enabled"] is True
    assert entry["allowed_task_types"] == [
        "automation",
        "backlog-governance",
        "ci-cd",
        "documentation",
        "repository-maintenance",
    ]
    assert entry["codex_environment"] == "portfolio-tasks-codex-production"
    assert entry["workflow_ref"] == "Young-Consultations/portfolio-tasks/.github/workflows/codex-execute.yml@main"
    assert entry["draft_pr_only"] is True


def test_workflows_do_not_use_pull_request_target_or_merge():
    for workflow in Path(".github/workflows").glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        assert "pull_request_target" not in text
        assert "gh pr merge" not in text
        assert "--auto" not in text


def test_router_uses_least_privilege_permissions():
    text = Path(".github/workflows/codex-router.yml").read_text(encoding="utf-8")
    assert "contents: read" in text
    assert "actions: read" in text
    assert "contents: write" not in text
    assert "pull-requests: write" not in text


def test_router_checkout_uses_policy_repository():
    text = Path(".github/workflows/codex-router.yml").read_text(encoding="utf-8")
    assert "repository: Young-Consultations/.github" in text
    assert "persist-credentials: false" in text
