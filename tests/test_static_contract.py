import json
import re
from pathlib import Path

import yaml


WORKFLOWS = Path(".github/workflows")
CONTRACT_WORKFLOW = WORKFLOWS / "ai-sdlc-contract-tests.yml"


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
        assert entry["contract_version"] == "ai-sdlc-contract/v2", name


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
    for workflow in WORKFLOWS.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        assert "pull_request_target" not in text
        assert "gh pr merge" not in text
        assert "--auto" not in text


def test_workflow_yaml_syntax():
    for workflow in WORKFLOWS.glob("*.yml"):
        assert yaml.safe_load(workflow.read_text(encoding="utf-8")) is not None


def test_contract_workflow_runs_for_every_pull_request():
    workflow = yaml.load(
        CONTRACT_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    assert workflow["on"]["pull_request"] in (None, "")


def test_contract_json_syntax():
    for path in Path("contracts").rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_third_party_actions_are_pinned_to_full_shas():
    action = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)
    for workflow in WORKFLOWS.glob("*.yml"):
        for reference in action.findall(workflow.read_text(encoding="utf-8")):
            owner, _, version = reference.partition("@")
            if owner.startswith("Young-Consultations/"):
                continue
            assert re.fullmatch(r"[0-9a-f]{40}", version), (workflow, reference)


def test_contract_workflow_is_read_only_and_has_no_execution_path():
    text = CONTRACT_WORKFLOW.read_text(encoding="utf-8")
    assert text.startswith("name: AI-SDLC Contract Tests\n")
    assert re.search(r"^permissions:\n  contents: read$", text, re.MULTILINE)
    assert "contents: write" not in text
    assert "actions: write" not in text
    assert "pull-requests: write" not in text
    assert "issues: write" not in text
    assert "secrets." not in text
    for forbidden in (
        "pull_request_target",
        "codex_router.py dispatch",
        "gh workflow run",
        "repository_dispatch",
        "gh issue",
        "gh pr create",
        "git push",
    ):
        assert forbidden not in text


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


def test_router_installs_validator_dependencies_and_enforces_concurrency():
    text = Path(".github/workflows/codex-router.yml").read_text(encoding="utf-8")
    assert "--no-deps" not in text
    assert "concurrency_group: ${{ steps.validate.outputs.concurrency_group }}" in text
    assert "group: ${{ needs.route.outputs.concurrency_group }}" in text
    assert "cancel-in-progress: false" in text


def test_smoke_and_production_routes_select_modes_explicitly():
    router = Path(".github/workflows/codex-router.yml").read_text(encoding="utf-8")
    smoke = Path(".github/workflows/router-smoke-test.yml").read_text(encoding="utf-8")
    assert "default: implement" in router
    assert "EXECUTION_MODE: ${{ inputs.execution_mode }}" in router
    assert "execution_mode: verify" in smoke
