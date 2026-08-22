import json
import hashlib
import re
import subprocess
from pathlib import Path

import yaml


WORKFLOWS = Path(".github/workflows")
CONTRACT_WORKFLOW = WORKFLOWS / "ai-sdlc-contract-tests.yml"
ROUTER_WORKFLOW = WORKFLOWS / "codex-router.yml"
ORGANIZATION_REPOSITORY = "Young-Consultations/.github"
OBSOLETE_EXECUTOR_INPUTS = {
    "project_component",
    "dependency_status",
    "codex_environment",
}


def test_registry_json_syntax_and_required_fields():
    data = json.loads(Path("config/codex-repositories.json").read_text(encoding="utf-8"))
    assert data["registry_format_version"] == 1
    repos = data["repositories"]
    assert "Young-Consultations/slugger" in repos
    assert "Young-Consultations/consulting-playbook" in repos
    assert "Young-Consultations/portfolio-tasks" in repos
    assert "Young-Consultations/.github" in repos
    assert len(repos) == 4
    activation = json.loads(Path("config/codex-activation.json").read_text(encoding="utf-8"))
    assert activation["activation_format_version"] == 1
    assert activation["targets"] == {name: False for name in repos}
    for name, entry in repos.items():
        assert "enabled" not in entry, name
        assert entry["allowed_task_types"], name
        assert entry["codex_environment"], name
        assert entry["max_parallel_tasks"] >= 1, name
        assert entry["draft_pr_only"] is True, name
        assert entry["workflow_ref"] == f"{name}/.github/workflows/codex-execute.yml@codex-adapter-v2.3.1", name
        assert entry["contract_version"] == "ai-sdlc-contract/v2", name
        assert entry["conformance"]["adapter_ref"] == "codex-adapter-v2.3.1", name
        assert entry["conformance"]["status"] == "pass", name
        assert entry["conformance"]["activation_evidence_sufficient"] is True, name


def test_activation_change_does_not_change_compatibility_contents(tmp_path):
    capability = Path("config/codex-repositories.json").read_bytes()
    release = Path("release/release-manifest.json").read_bytes()
    activation = json.loads(Path("config/codex-activation.json").read_text())
    activation["targets"]["Young-Consultations/.github"] = True
    (tmp_path / "activation.json").write_text(json.dumps(activation))

    assert hashlib.sha256(capability).hexdigest() == hashlib.sha256(
        Path("config/codex-repositories.json").read_bytes()
    ).hexdigest()
    assert hashlib.sha256(release).hexdigest() == hashlib.sha256(
        Path("release/release-manifest.json").read_bytes()
    ).hexdigest()


def test_github_target_is_bounded_and_idempotent():
    data = json.loads(Path("config/codex-repositories.json").read_text())
    entry = data["repositories"]["Young-Consultations/.github"]
    assert entry["allowed_task_types"] == ["ci-cd", "documentation", "repository-maintenance", "testing"]
    assert entry["contract_version"] == "ai-sdlc-contract/v2"
    assert entry["draft_pr_only"] is True
    assert entry["idempotency"] == {
        "branch_identity": "delivery_id",
        "ownership_marker": "ai-sdlc-delivery-id",
        "requires_preflight": True,
        "requires_fail_closed_reuse": True,
        "requires_create_race_requery": True,
        "terminal_reuse_status": "duplicate-reused",
    }


def test_organization_target_executor_is_canonical_v2_path():
    workflow = (WORKFLOWS / "codex-execute.yml").read_text()
    assert "execution_input_json:" in workflow
    assert "concurrency_group:" in workflow
    assert "scripts/codex_target_adapter.py" in workflow
    assert (
        "Young-Consultations/.github/.github/workflows/"
        "codex-result-receiver.yml@ai-sdlc-v2.3.1"
    ) in workflow
    assert "CODEX_TRUSTED_JOURNAL_AUTHORS" not in workflow
    assert {
        "ai-sdlc-contract-tests.yml",
        "codex-execute.yml",
        "codex-router.yml",
        "router-smoke-test.yml",
    }.issubset({path.name for path in WORKFLOWS.glob("*.yml")})


def test_result_receiver_owns_journal_author_policy():
    receiver = (WORKFLOWS / "codex-result-receiver.yml").read_text(encoding="utf-8")
    action = Path("actions/codex-result-receiver/action.yml").read_text(encoding="utf-8")
    script = Path("scripts/codex_result_receiver.py").read_text(encoding="utf-8")
    policy = json.loads(Path("config/codex-result-trust.json").read_text(encoding="utf-8"))

    assert "CODEX_TRUSTED_JOURNAL_AUTHORS" not in receiver
    assert "actions/checkout@" not in receiver
    assert receiver.count(
        "Young-Consultations/.github/actions/codex-result-receiver@ai-sdlc-v2.3.1"
    ) == 1
    assert '$GITHUB_ACTION_PATH/../../scripts/codex_result_receiver.py' in action
    assert "config/codex-result-trust.json" in script
    assert policy == {
        "policy_format_version": 2,
        "trusted_admission_authors": ["mightyjoe909"],
        "trusted_result_authors": ["github-actions[bot]"],
    }


def test_router_is_the_only_organization_dispatch_boundary():
    dispatchers = []
    for workflow in WORKFLOWS.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        has_dispatch = any(
            marker in text
            for marker in (
                "codex_router.py dispatch",
                "gh workflow run",
                "repository_dispatch",
            )
        )
        if has_dispatch:
            dispatchers.append(workflow)
    assert dispatchers == [ROUTER_WORKFLOW]


def test_active_workflows_do_not_expose_obsolete_executor_inputs():
    for workflow in WORKFLOWS.glob("*.yml"):
        document = yaml.load(workflow.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        triggers = document.get("on", {}) or {}
        for trigger_name in ("workflow_call", "workflow_dispatch"):
            trigger = triggers.get(trigger_name, {}) or {}
            inputs = set((trigger.get("inputs", {}) or {}).keys())
            assert inputs.isdisjoint(OBSOLETE_EXECUTOR_INPUTS), (workflow, inputs)


def test_portfolio_tasks_registration_contract():
    data = json.loads(Path("config/codex-repositories.json").read_text(encoding="utf-8"))
    entry = data["repositories"]["Young-Consultations/portfolio-tasks"]
    assert entry["allowed_task_types"] == [
        "automation",
        "backlog-governance",
        "ci-cd",
        "documentation",
        "repository-maintenance",
    ]
    assert entry["codex_environment"] == "portfolio-tasks-codex-production"
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


def test_repository_does_not_track_gitlinks():
    result = subprocess.run(
        ["git", "ls-files", "-s"],
        check=True,
        capture_output=True,
        text=True,
    )
    gitlinks = [
        line.split("\t", 1)[1]
        for line in result.stdout.splitlines()
        if line.startswith("160000 ")
    ]
    assert gitlinks == []


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


def test_router_loads_current_activation_outside_immutable_checkout():
    text = Path(".github/workflows/codex-router.yml").read_text(encoding="utf-8")
    assert text.count("ref: ${{ github.workflow_sha }}") == 2
    assert text.count("ref: main") == 2
    assert text.count("sparse-checkout: config/codex-activation.json") == 2
    assert "CODEX_ACTIVATION_PATH: ${{ github.workspace }}/control-plane/config/codex-activation.json" in text
    assert "python3 immutable-policy/scripts/codex_router.py validate" in text
    assert "python3 immutable-policy/scripts/codex_router.py dispatch" in text


def test_activation_changes_trigger_target_compatibility():
    text = Path(".github/workflows/target-workflow-compatibility.yml").read_text(encoding="utf-8")
    assert "- 'config/codex-activation.json'" in text


def test_manual_target_compatibility_can_verify_disabled_targets():
    text = Path(".github/workflows/target-workflow-compatibility.yml").read_text(encoding="utf-8")
    assert "repository:" in text
    assert "default: all" in text
    assert "SELECTED_REPOSITORY: ${{ inputs.repository || 'all' }}" in text
    for repository in (
        "Young-Consultations/.github",
        "Young-Consultations/portfolio-tasks",
        "Young-Consultations/consulting-playbook",
        "Young-Consultations/slugger",
    ):
        assert f'verify_repository "{repository}"' in text
    assert '--repository "$repository"' in text
    assert "path: reports/*.json" in text


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
