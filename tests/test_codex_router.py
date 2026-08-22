import json
import os
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts import codex_router


TEST_ADAPTER_TAG = "codex-adapter-v2.0.0"


BASE_TASK = {
    "contract_version": "ai-sdlc-contract/v2",
    "task_id": "portfolio-8-attempt-1",
    "source_issue": "Young-Consultations/portfolio-tasks#8",
    "status": "approved",
    "executor": "codex",
    "project": "Publication Output",
    "priority": "p2",
    "task_type": "automation",
    "target_repository": "Young-Consultations/portfolio-tasks",
    "parallel_safe": False,
    "dependencies": [],
    "risk": "low",
    "scope": "small",
    "instructions": "Make the approved change and open a draft pull request.",
    "created_by": "portfolio-tasks",
}


@pytest.fixture(autouse=True)
def enabled_in_process_routing(monkeypatch):
    """Direct dispatch unit tests operate on an explicitly active snapshot."""
    original = codex_router.routing_configuration

    def active_configuration():
        repositories, _ = original()
        return repositories, {repository: True for repository in repositories}

    monkeypatch.setattr(codex_router, "routing_configuration", active_configuration)


def run_router(
    *, github_output=None, execution_mode=None, enable_target=True,
    workflow_revision=TEST_ADAPTER_TAG, with_conformance=True, **changes,
):
    task = {**BASE_TASK, **changes}
    env = {key: value for key, value in os.environ.items() if key != "GITHUB_OUTPUT"}
    env["TASK_PAYLOAD"] = json.dumps(task)
    registry = json.loads(Path("config/codex-repositories.json").read_text(encoding="utf-8"))
    activation = json.loads(Path("config/codex-activation.json").read_text(encoding="utf-8"))
    if enable_target and task["target_repository"] in registry["repositories"]:
        entry = registry["repositories"][task["target_repository"]]
        activation["targets"][task["target_repository"]] = True
        entry["workflow_ref"] = entry["workflow_ref"].rsplit("@", 1)[0] + "@" + workflow_revision
        entry["conformance"] = {
            "fixture_set": "TC-MVP-CI-001",
            "fixture_version": "2.3.0",
            "compatibility_sha": "1" * 40,
            "adapter_ref": workflow_revision,
            "adapter_commit_sha": "2" * 40,
            "report_path": ".ai-sdlc/conformance/tc-mvp-ci-001.json",
            "report_sha256": "3" * 64,
            "status": "pass",
            "activation_evidence_sufficient": True,
        } if with_conformance else None
    if execution_mode is not None:
        env["EXECUTION_MODE"] = execution_mode
    else:
        env.pop("EXECUTION_MODE", None)
    if github_output is not None:
        env["GITHUB_OUTPUT"] = os.fspath(github_output)
    registry_path = Path("config/codex-repositories.json")
    activation_path = Path("config/codex-activation.json")
    original_registry = registry_path.read_text(encoding="utf-8")
    original_activation = activation_path.read_text(encoding="utf-8")
    try:
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        activation_path.write_text(json.dumps(activation), encoding="utf-8")
        result = subprocess.run(
            ["python3", "scripts/codex_router.py", "validate"], env=env,
            text=True, capture_output=True,
        )
    finally:
        registry_path.write_text(original_registry, encoding="utf-8")
        activation_path.write_text(original_activation, encoding="utf-8")
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
    ],
)
def test_registered_routes_emit_one_execution_contract(repository, task_type):
    result = run_router(target_repository=repository, task_type=task_type)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output(result, "execution_input"))
    assert set(payload) == {
        "contract_version", "correlation_id", "delivery_id", "source_issue", "target_repository",
        "task_type", "project", "priority", "executor", "parallel_safe", "draft_pr_only",
        "instructions", "requested_branch", "concurrency_group", "timeout_minutes",
        "execution_mode",
    }
    assert payload["target_repository"] == repository
    assert payload["project"] == BASE_TASK["project"]
    assert payload["execution_mode"] == "implement"
    assert payload["delivery_id"] == BASE_TASK["task_id"]


def test_router_emits_explicit_verify_mode_without_inspecting_instructions():
    result = run_router(
        execution_mode="verify",
        instructions="Implement everything and create a pull request.",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(output(result, "execution_input"))["execution_mode"] == "verify"


def test_invalid_execution_mode_is_rejected():
    result = run_router(execution_mode="dry-run")
    assert result.returncode == 1
    assert output(result, "failure_category") == "contract-validation"


def test_unknown_repository_is_canonical_routing_rejection():
    result = run_router(target_repository="Young-Consultations/unknown")
    assert result.returncode == 1
    assert output(result, "failure_category") == "repository-routing"


def test_disabled_repository_is_rejected():
    result = run_router(enable_target=False)
    assert result.returncode == 1
    assert output(result, "failure_category") == "repository-routing"
    assert json.loads(output(result, "execution_result"))["execution_status"] == "rejected"


def test_unsupported_task_type_is_rejected():
    result = run_router(task_type="security")
    assert result.returncode == 1
    assert output(result, "failure_category") == "repository-routing"


def test_unresolved_dependency_is_rejected():
    result = run_router(dependencies=["portfolio-7"])
    assert result.returncode == 1
    assert output(result, "failure_category") == "dependency"


def test_unsupported_contract_version_is_rejected():
    result = run_router(contract_version="ai-sdlc-contract/v1")
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
    assert output(run_router(status="queued"), "failure_category") == "authorization"
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
        "delivery_id": BASE_TASK["task_id"],
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
        "delivery_id",
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


@pytest.mark.parametrize("workflow_revision", [
    "main",
    "0123456789abcdef0123456789abcdef01234567",
    "codex-adapter-v2",
])
def test_enabled_activation_rejects_non_release_tag_refs(workflow_revision):
    result = run_router(workflow_revision=workflow_revision)
    assert result.returncode == 1
    assert output(result, "failure_category") == "repository-routing"


def test_enabled_activation_accepts_dispatchable_immutable_adapter_tag():
    result = run_router(workflow_revision="codex-adapter-v2.1.3-rc.1")
    assert result.returncode == 0, result.stdout + result.stderr
    assert output(result, "workflow_ref").endswith("@codex-adapter-v2.1.3-rc.1")


def test_enabled_activation_rejects_missing_shared_oracle_evidence():
    result = run_router(with_conformance=False)
    assert result.returncode == 1
    assert output(result, "failure_category") == "repository-routing"
    assert "TC-MVP-CI-001" in output(result, "diagnostic_summary")


def test_repository_specific_configuration_is_registry_only():
    router = open("scripts/codex_router.py", encoding="utf-8").read()
    for repository in (
        "Young-Consultations/slugger",
        "Young-Consultations/consulting-playbook",
        "Young-Consultations/portfolio-tasks",
    ):
        assert repository not in router


def execution_for(repository, task_type):
    result = run_router(target_repository=repository, task_type=task_type)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(output(result, "execution_input"))


@pytest.mark.parametrize(
    ("repository", "task_type"),
    [
        ("Young-Consultations/portfolio-tasks", "repository-maintenance"),
    ],
)
def test_dispatch_uses_canonical_json_transport_for_every_repository(
    repository, task_type, monkeypatch,
):
    execution = execution_for(repository, task_type)
    registry = json.loads(open("config/codex-repositories.json", encoding="utf-8").read())
    workflow_ref = registry["repositories"][repository]["workflow_ref"]
    calls = []

    monkeypatch.setenv("EXECUTION_INPUT", json.dumps(execution))
    monkeypatch.setenv("WORKFLOW_REF", workflow_ref)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.setattr(codex_router.subprocess, "run", lambda cmd, **kwargs: calls.append((cmd, kwargs)))

    codex_router.dispatch()

    assert calls[0][0][1:3] == ["api", f"repos/{repository}/issues/8/comments"]
    cmd, kwargs = calls[-1]
    fields = [cmd[index + 1] for index, value in enumerate(cmd) if value == "-f"]
    assert len(fields) == 2
    assert [field.split("=", 1)[0] for field in fields] == [
        "execution_input_json", "concurrency_group",
    ]
    transported = json.loads(fields[0].split("=", 1)[1])
    assert transported == execution
    assert isinstance(transported["parallel_safe"], bool)
    assert transported["correlation_id"] == execution["correlation_id"]
    assert transported["requested_branch"] == execution["requested_branch"]
    assert transported["target_repository"] == repository
    assert fields[1] == f"concurrency_group={execution['concurrency_group']}"
    assert kwargs == {"check": True, "text": True, "capture_output": True}


def test_portfolio_tasks_dispatch_command_matches_workflow_interface(monkeypatch):
    repository = "Young-Consultations/portfolio-tasks"
    execution = execution_for(repository, "repository-maintenance")
    monkeypatch.setenv("EXECUTION_INPUT", json.dumps(execution))
    monkeypatch.setenv(
        "WORKFLOW_REF",
        f"{repository}/.github/workflows/codex-execute.yml@codex-adapter-v2.3.1",
    )
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    commands = []
    monkeypatch.setattr(codex_router.subprocess, "run", lambda cmd, **kwargs: commands.append(cmd))

    codex_router.dispatch()

    assert commands[0][1:3] == ["api", f"repos/{repository}/issues/8/comments"]
    assert commands[-1][:8] == [
        "gh", "workflow", "run", "codex-execute.yml", "--repo", repository,
        "--ref", "codex-adapter-v2.3.1",
    ]
    assert commands[-1][8::2] == ["-f", "-f"]


def test_dispatch_rejects_invalid_execution_without_running_gh(monkeypatch):
    execution = execution_for("Young-Consultations/portfolio-tasks", "automation")
    execution["parallel_safe"] = "false"
    monkeypatch.setenv("EXECUTION_INPUT", json.dumps(execution))
    monkeypatch.setenv(
        "WORKFLOW_REF",
        "Young-Consultations/portfolio-tasks/.github/workflows/codex-execute.yml@codex-adapter-v2.3.1",
    )
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.setattr(
        codex_router.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("gh must not run for invalid input"),
    )

    with pytest.raises(SystemExit):
        codex_router.dispatch()


def test_github_422_dispatch_failure_is_publication(monkeypatch, capsys):
    execution = execution_for("Young-Consultations/portfolio-tasks", "automation")
    monkeypatch.setenv("EXECUTION_INPUT", json.dumps(execution))
    monkeypatch.setenv(
        "WORKFLOW_REF",
        "Young-Consultations/portfolio-tasks/.github/workflows/codex-execute.yml@codex-adapter-v2.3.1",
    )
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    failure = subprocess.CalledProcessError(1, ["gh"], stderr="HTTP 422: Unexpected inputs provided")
    monkeypatch.setattr(codex_router.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(failure))

    with pytest.raises(SystemExit):
        codex_router.dispatch()

    assert "failure_category=publication" in capsys.readouterr().out
