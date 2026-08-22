from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_target_workflows", ROOT / "scripts/verify_target_workflows.py")
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

FIXTURE = ROOT / "tests/fixtures/target_workflows/portfolio-tasks-codex-execute.yml"
CANONICAL = FIXTURE.read_text(encoding="utf-8")


def workflow(inputs: str) -> str:
    return "on:\n  workflow_dispatch:\n    inputs:\n" + inputs


def canonical_inputs(extra: str = "") -> str:
    return (
        "      execution_input_json: {required: true, type: string}\n"
        "      concurrency_group: {required: true, type: string}\n"
        + extra
    )


def registry(tmp_path: Path, entries: dict) -> Path:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"registry_format_version": 1, "repositories": entries}), encoding="utf-8")
    return path


def activation(tmp_path: Path, targets: dict[str, bool]) -> Path:
    path = tmp_path / "activation.json"
    path.write_text(json.dumps({"activation_format_version": 1, "targets": targets}), encoding="utf-8")
    return path


def entry(repo: str = "org/repo", **changes):
    adapter_ref = "codex-adapter-v2.0.0"
    value = {
        "workflow_ref": f"{repo}/.github/workflows/codex-execute.yml@{adapter_ref}",
        "contract_version": checker.CANONICAL_VERSION,
        "draft_pr_only": True,
        "max_parallel_tasks": 1,
        "conformance": {
            "fixture_set": "TC-MVP-CI-001",
            "fixture_version": checker.release_fixture_version(),
            "compatibility_sha": "1" * 40,
            "adapter_ref": adapter_ref,
            "adapter_commit_sha": "2" * 40,
            "report_path": ".ai-sdlc/conformance/tc-mvp-ci-001.json",
            "report_sha256": "3" * 64,
            "status": "pass",
            "activation_evidence_sufficient": True,
        },
        "idempotency": {
            "branch_identity": "delivery_id",
            "ownership_marker": "ai-sdlc-delivery-id",
            "requires_preflight": True,
            "requires_fail_closed_reuse": True,
            "requires_create_race_requery": True,
            "terminal_reuse_status": "duplicate-reused",
        },
    }
    value.update(changes)
    if "workflow_ref" in changes and "conformance" not in changes:
        value["conformance"]["adapter_ref"] = value["workflow_ref"].rsplit("@", 1)[1]
    return value


def test_canonical_portfolio_tasks_interface():
    assert checker.verify_interface(CANONICAL) == (
        "exact two-input workflow_dispatch + receiver-compatible consumer"
    )


def test_wrapper_comments_cannot_substitute_for_executable_adapter_evidence():
    stripped = "\n".join(
        line for line in CANONICAL.splitlines()
        if "preflight" not in line
        and "ownership marker" not in line
        and "create-race" not in line
        and "duplicate-reused" not in line
    )
    assert checker.verify_interface(stripped) == (
        "exact two-input workflow_dispatch + receiver-compatible consumer"
    )


def test_target_cannot_supply_control_plane_journal_author_policy():
    source = CANONICAL.replace(
        "CODEX_RESULT_TOKEN: ${{ secrets.CODEX_RESULT_TOKEN }}",
        "CODEX_RESULT_TOKEN: ${{ secrets.CODEX_RESULT_TOKEN }}\n"
        "      CODEX_TRUSTED_JOURNAL_AUTHORS: ${{ secrets.CODEX_TRUSTED_JOURNAL_AUTHORS }}",
    )
    with pytest.raises(checker.CompatibilityError, match="must not supply"):
        checker.verify_interface(source)


def test_target_receiver_pin_must_be_immutable():
    source = CANONICAL.replace("@0123456789abcdef0123456789abcdef01234567", "@main")
    with pytest.raises(checker.CompatibilityError, match="immutable"):
        checker.verify_interface(source)


def test_canonical_receiver_accepts_only_result_delivery_credential():
    source = (ROOT / ".github/workflows/codex-result-receiver.yml").read_text()
    assert checker.verify_receiver_interface(source) == "ai-sdlc-v2.3.1"
    checker.verify_receiver_action(
        (ROOT / "actions/codex-result-receiver/action.yml").read_text()
    )

    incompatible = source.replace(
        "    outputs:",
        "      CODEX_TRUSTED_JOURNAL_AUTHORS:\n"
        "        required: true\n"
        "    outputs:",
        1,
    )
    with pytest.raises(checker.CompatibilityError, match="only CODEX_RESULT_TOKEN"):
        checker.verify_receiver_interface(incompatible)


def test_receiver_cannot_checkout_policy_from_caller_context():
    source = (ROOT / ".github/workflows/codex-result-receiver.yml").read_text()
    unsafe = source.replace(
        "    steps:\n",
        "    steps:\n"
        "      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683\n",
        1,
    )
    with pytest.raises(checker.CompatibilityError, match="caller-controlled"):
        checker.verify_receiver_interface(unsafe)


def test_receiver_action_bundle_pin_must_be_immutable():
    source = (ROOT / ".github/workflows/codex-result-receiver.yml").read_text()
    mutable = source.replace("@ai-sdlc-v2.3.1", "@main")
    with pytest.raises(checker.CompatibilityError, match="immutable"):
        checker.verify_receiver_interface(mutable)


def test_live_receiver_bundle_requires_nonempty_control_plane_trust():
    script = (ROOT / "scripts/codex_result_receiver.py").read_text()
    with pytest.raises(checker.CompatibilityError, match="reviewed non-empty"):
        checker.verify_receiver_bundle_policy(
            script,
            b'{"policy_format_version":2,"trusted_admission_authors":[],"trusted_result_authors":["receiver[bot]"]}',
        )
    checker.verify_receiver_bundle_policy(
        script,
        b'{"policy_format_version":2,"trusted_admission_authors":["router[bot]"],"trusted_result_authors":["receiver[bot]"]}',
    )


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (workflow("      concurrency_group: {required: true, type: string}\n"), "missing execution_input_json"),
        (workflow("      execution_input_json: {required: true, type: string}\n"), "missing concurrency_group"),
        (workflow("      execution_input_json: {required: false, type: string}\n      concurrency_group: {required: true, type: string}\n"), "required must be true"),
        (workflow("      execution_input_json: {required: true, type: boolean}\n      concurrency_group: {required: true, type: string}\n"), "must have type string"),
        (workflow(canonical_inputs("      extra_required: {required: true, type: string}\n")), "unexpected inputs"),
    ],
)
def test_incompatible_interfaces(source, message):
    with pytest.raises(checker.CompatibilityError, match=message):
        checker.verify_interface(source)


def test_obsolete_field_by_field_workflow_rejected():
    fields = "".join(f"      {name}: {{required: true, type: string}}\n" for name in checker.CONTRACT_FIELDS)
    source = workflow(canonical_inputs(fields))
    with pytest.raises(checker.CompatibilityError, match="unexpected inputs"):
        checker.verify_interface(source)


def test_repository_mismatch(tmp_path):
    path = registry(tmp_path, {"org/repo": entry("other/repo")})
    with pytest.raises(checker.CompatibilityError, match="repository mismatch"):
        checker.load_registry(path)


@pytest.mark.parametrize("reference", ["bad", "org/repo/file.yml@main", "org/repo/.github/workflows/x.yml", "org/repo/.github/workflows/x.yml@main@next"])
def test_malformed_workflow_ref(reference):
    with pytest.raises(checker.CompatibilityError, match="malformed"):
        checker.parse_workflow_ref(reference)


def test_disabled_activation_entry_is_skipped(tmp_path):
    path = registry(tmp_path, {"org/repo": entry()})
    entries = checker.load_registry(path)
    with patch.object(checker, "fetch_workflow") as fetch:
        report = checker.verify_registry(entries, None, activation={"org/repo": False})
        assert report[0]["result"] == "not-evaluated: target disabled"
        fetch.assert_not_called()


def test_all_disabled_registry_cannot_report_organization_wide_pass(tmp_path):
    registry_path = registry(tmp_path, {"org/repo": entry()})
    activation_path = activation(tmp_path, {"org/repo": False})
    report_path = tmp_path / "report.json"

    assert checker.main([
        "--registry", str(registry_path),
        "--activation", str(activation_path),
        "--report", str(report_path),
    ]) == 1
    assert json.loads(report_path.read_text())["targets"][0]["result"] == (
        "not-evaluated: target disabled"
    )


def test_disabled_target_can_be_explicitly_verified_before_activation(tmp_path):
    entries = checker.load_registry(registry(tmp_path, {"org/repo": entry()}))
    with (
        patch.object(checker, "fetch_ref_commit", return_value="2" * 40),
        patch.object(checker, "fetch_workflow", return_value=CANONICAL),
        patch.object(checker, "verify_receiver_at_ref"),
        patch.object(checker, "verify_conformance_report"),
    ):
        report = checker.verify_registry(
            entries, "fake-token", selected_repository="org/repo",
            activation={"org/repo": False},
        )
    assert report[0]["result"] == "pass"


def test_enabled_activation_requires_reviewed_shared_oracle_evidence(tmp_path):
    value = entry(conformance=None)
    entries = checker.load_registry(registry(tmp_path, {"org/repo": value}))
    with pytest.raises(checker.CompatibilityError, match="TC-MVP-CI-001"):
        checker.load_activation(activation(tmp_path, {"org/repo": True}), entries)


def test_contract_version_mismatch(tmp_path):
    path = registry(tmp_path, {"org/repo": entry(contract_version="ai-sdlc-contract/v1")})
    with pytest.raises(checker.CompatibilityError, match="contract-version mismatch"):
        checker.load_registry(path)


@pytest.mark.parametrize("revision", [
    "main",
    "0123456789abcdef0123456789abcdef01234567",
    "codex-adapter-v2.0",
])
def test_enabled_activation_requires_governed_adapter_release_tag(tmp_path, revision):
    workflow_ref = f"org/repo/.github/workflows/codex-execute.yml@{revision}"
    path = registry(tmp_path, {"org/repo": entry(workflow_ref=workflow_ref)})
    entries = checker.load_registry(path)
    with pytest.raises(checker.CompatibilityError, match="codex-adapter-v"):
        checker.load_activation(activation(tmp_path, {"org/repo": True}), entries)


def test_missing_workflow_is_reported_without_network(tmp_path):
    entries = checker.load_registry(registry(tmp_path, {"org/repo": entry()}))
    with (
        patch.object(checker, "fetch_ref_commit", return_value="2" * 40),
        patch.object(checker, "fetch_workflow", side_effect=checker.CompatibilityError("workflow is unavailable at registered ref")),
    ):
        report = checker.verify_registry(entries, "fake-token")
    assert report[0]["result"] == "fail: workflow is unavailable at registered ref"


def test_network_fetch_is_mocked_for_success(tmp_path):
    entries = checker.load_registry(registry(tmp_path, {"org/repo": entry()}))
    with (
        patch.object(checker, "fetch_ref_commit", return_value="2" * 40),
        patch.object(checker, "fetch_workflow", return_value=CANONICAL) as fetch,
        patch.object(checker, "verify_receiver_at_ref") as receiver_check,
        patch.object(checker, "verify_conformance_report") as report_check,
    ):
        report = checker.verify_registry(entries, "fake-token")
    fetch.assert_called_once_with("org/repo", ".github/workflows/codex-execute.yml", "codex-adapter-v2.0.0", "fake-token")
    receiver_check.assert_called_once_with("0123456789abcdef0123456789abcdef01234567", "fake-token")
    report_check.assert_called_once_with(
        "org/repo",
        "codex-adapter-v2.0.0",
        ".github/workflows/codex-execute.yml",
        entries["org/repo"]["conformance"],
        "fake-token",
    )
    assert report[0]["result"] == "pass"


def complete_report(repository="org/repo"):
    fixture = json.loads((ROOT / "tests/fixtures/mvp-v2/manifest.json").read_text())
    return {
        "report_version": "1.0",
        "repository": repository,
        "adapter_revision": "sha256:" + "4" * 64,
        "compatibility_sha": "1" * 40,
        "fixture_set": "TC-MVP-CI-001",
        "fixture_version": checker.release_fixture_version(),
        "production_readiness_claim": False,
        "activation_requested": False,
        "activation_evidence_sufficient": True,
        "effect_traps": {name: 0 for name in checker.REQUIRED_ZERO_EFFECTS},
        "scenario_results": [
            {"id": scenario, "result": "pass"} for scenario in fixture["scenarios"]
        ],
        "failures": [],
    }


def test_conformance_report_must_be_digest_bound_complete_and_effect_free():
    raw = (json.dumps(complete_report(), sort_keys=True) + "\n").encode()
    evidence = entry()["conformance"]
    evidence["report_sha256"] = hashlib.sha256(raw).hexdigest()

    with (
        patch.object(checker, "fetch_content", return_value=raw),
        patch.object(checker, "verify_conformance_pin", return_value="sha256:" + "4" * 64),
    ):
        checker.verify_conformance_report(
            "org/repo", "codex-adapter-v2.0.0", ".github/workflows/codex-execute.yml", evidence, None,
        )

    incomplete = complete_report()
    incomplete["scenario_results"].pop()
    invalid_raw = (json.dumps(incomplete, sort_keys=True) + "\n").encode()
    evidence["report_sha256"] = hashlib.sha256(invalid_raw).hexdigest()
    with (
        patch.object(checker, "fetch_content", return_value=invalid_raw),
        patch.object(checker, "verify_conformance_pin", return_value="sha256:" + "4" * 64),
        pytest.raises(checker.CompatibilityError, match="complete shared oracle"),
    ):
        checker.verify_conformance_report(
            "org/repo", "codex-adapter-v2.0.0", ".github/workflows/codex-execute.yml", evidence, None,
        )


def test_conformance_pin_revision_is_non_recursive_and_file_bound():
    evidence = entry()["conformance"]
    compatibility_files = {
        path: checker.git_blob_sha1((ROOT / path).read_bytes())
        for path in checker.PINNED_COMPATIBILITY_FILES
    }
    target_content = {
        ".github/workflows/codex-execute.yml": b"workflow\n",
        "scripts/codex_target_adapter.py": b"adapter\n",
        "scripts/run_tc_mvp_ci_001.py": b"harness\n",
    }
    pin = {
        "pin_format_version": 2,
        "organization_repository": "Young-Consultations/.github",
        "compatibility_sha": evidence["compatibility_sha"],
        "fixture_set": "TC-MVP-CI-001",
        "fixture_version": evidence["fixture_version"],
        "adapter_revision": "",
        "compatibility_files": compatibility_files,
        "target_files": {
            path: checker.git_blob_sha1(content) for path, content in target_content.items()
        },
    }
    pin["adapter_revision"] = checker.conformance_pin_revision(pin)
    pin_raw = json.dumps(pin).encode()

    def content(repository, path, ref, token):
        if path == checker.CONFORMANCE_PIN_PATH:
            return pin_raw
        if path in target_content and repository == "org/repo":
            return target_content[path]
        return (ROOT / path).read_bytes()

    with patch.object(checker, "fetch_content", side_effect=content):
        revision = checker.verify_conformance_pin(
            "org/repo",
            "codex-adapter-v2.0.0",
            ".github/workflows/codex-execute.yml",
            evidence,
            None,
        )
    assert revision == pin["adapter_revision"]
    assert revision.startswith("sha256:")
    assert revision != evidence["adapter_commit_sha"]


def test_conformance_pin_rejects_commit_sha_as_report_revision():
    pin = {
        "pin_format_version": 2,
        "organization_repository": "Young-Consultations/.github",
        "compatibility_sha": "1" * 40,
        "fixture_set": "TC-MVP-CI-001",
        "fixture_version": checker.release_fixture_version(),
        "adapter_revision": "2" * 40,
        "compatibility_files": {path: "3" * 40 for path in checker.PINNED_COMPATIBILITY_FILES},
        "target_files": {
            ".github/workflows/codex-execute.yml": "3" * 40,
            "scripts/codex_target_adapter.py": "3" * 40,
            "scripts/run_tc_mvp_ci_001.py": "3" * 40,
        },
    }
    with (
        patch.object(checker, "fetch_content", return_value=json.dumps(pin).encode()),
        pytest.raises(checker.CompatibilityError, match="revision"),
    ):
        checker.verify_conformance_pin(
            "org/repo",
            "codex-adapter-v2.0.0",
            ".github/workflows/codex-execute.yml",
            entry()["conformance"],
            None,
        )


def test_conformance_pin_requires_executed_adapter():
    evidence = entry()["conformance"]
    pin = {
        "pin_format_version": 2,
        "organization_repository": "Young-Consultations/.github",
        "compatibility_sha": evidence["compatibility_sha"],
        "fixture_set": "TC-MVP-CI-001",
        "fixture_version": evidence["fixture_version"],
        "adapter_revision": "sha256:" + "2" * 64,
        "compatibility_files": {
            path: "3" * 40 for path in checker.PINNED_COMPATIBILITY_FILES
        },
        "target_files": {
            ".github/workflows/codex-execute.yml": "3" * 40,
            "scripts/run_tc_mvp_ci_001.py": "3" * 40,
        },
    }
    with (
        patch.object(checker, "fetch_content", return_value=json.dumps(pin).encode()),
        pytest.raises(checker.CompatibilityError, match="required compatibility and target files"),
    ):
        checker.verify_conformance_pin(
            "org/repo",
            "codex-adapter-v2.0.0",
            ".github/workflows/codex-execute.yml",
            evidence,
            None,
        )


def test_fetch_workflow_accepts_line_wrapped_contents_api_payload():
    content = base64.encodebytes(CANONICAL.encode("utf-8")).decode("ascii")
    response = io.BytesIO(json.dumps({"content": content}).encode("utf-8"))

    with patch.object(checker.urllib.request, "urlopen", return_value=response):
        assert checker.fetch_workflow(
            "org/repo", ".github/workflows/codex-execute.yml", "fixed-ref", "fake-token"
        ) == CANONICAL


def test_main_keeps_diagnostics_and_results_visible_with_actions_summary(tmp_path, capsys):
    summary = tmp_path / "summary.md"
    report = tmp_path / "report.json"
    registry_path = registry(tmp_path, {"org/repo": entry()})

    with patch.dict(checker.os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}):
        assert checker.main([
            "--fixtures-only", "--registry", str(registry_path), "--report", str(report)
        ]) == 0

    captured = capsys.readouterr()
    assert "AI-SDLC target compatibility" in captured.out
    assert "loaded 1 registry entries" in captured.err
    assert "checked=1, nonpassing=0" in captured.err
    assert "AI-SDLC target compatibility" in summary.read_text(encoding="utf-8")


def test_fetch_failure_reports_http_status_and_url():
    error = checker.urllib.error.HTTPError(
        "https://api.github.test/workflow", 404, "Not Found", {}, None
    )

    with patch.object(checker.urllib.request, "urlopen", side_effect=error), pytest.raises(
        checker.CompatibilityError, match=r"HTTP 404: Not Found"
    ) as raised:
        checker.fetch_workflow("org/repo", ".github/workflows/codex-execute.yml", "missing")

    assert "api.github.com/repos/org/repo/contents/" in str(raised.value)


def test_all_canonical_router_inputs_must_be_declared():
    source = workflow(
        canonical_inputs("      execution_input_artifact: {required: false, type: string}\n")
    )
    with pytest.raises(checker.CompatibilityError, match="unexpected inputs"):
        checker.verify_interface(source)


def test_incompatible_required_input_is_rejected():
    source = workflow(
        "      execution_input_json: {required: true, type: string}\n"
        "      concurrency_group: {required: true, type: string}\n"
        "      extra_required: {required: true, type: string}\n"
    )
    with pytest.raises(checker.CompatibilityError, match="unexpected inputs"):
        checker.verify_interface(source)


def test_issue_to_codex_cannot_be_registered(tmp_path):
    path = registry(tmp_path, {"org/repo": entry(workflow_ref="org/repo/.github/workflows/issue-to-codex.yml@codex-adapter-v2.0.0")})
    with pytest.raises(checker.CompatibilityError, match="obsolete workflow_ref"):
        checker.load_registry(path)


def test_draft_only_must_remain_true(tmp_path):
    path = registry(tmp_path, {"org/repo": entry(draft_pr_only=False)})
    with pytest.raises(checker.CompatibilityError, match="draft-only"):
        checker.load_registry(path)


def test_deterministic_concurrency_policy_is_required(tmp_path):
    path = registry(tmp_path, {"org/repo": entry(max_parallel_tasks=0)})
    with pytest.raises(checker.CompatibilityError, match="deterministic concurrency"):
        checker.load_registry(path)


def test_duplicate_repository_registration_is_rejected(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text(
        '{"registry_format_version":1,"repositories":{"org/repo":'
        + json.dumps(entry())
        + ',"org/repo":'
        + json.dumps(entry())
        + '}}',
        encoding="utf-8",
    )
    with pytest.raises(checker.CompatibilityError, match="duplicate JSON key"):
        checker.load_registry(path)


def test_one_incompatible_target_does_not_block_unrelated_target(tmp_path):
    entries = checker.load_registry(registry(tmp_path, {"org/good": entry("org/good"), "org/bad": entry("org/bad")}))
    def fake_fetch(repo, path, ref, token):
        if repo == "org/bad":
            return workflow("      execution_input_json: {required: true, type: string}\n")
        return CANONICAL
    with (
        patch.object(checker, "fetch_ref_commit", return_value="2" * 40),
        patch.object(checker, "fetch_workflow", side_effect=fake_fetch),
        patch.object(checker, "verify_receiver_at_ref"),
        patch.object(checker, "verify_conformance_report"),
    ):
        report = checker.verify_registry(entries, None)
    assert report[0]["result"] == "pass"
    assert report[1]["result"].startswith("fail:")


def test_api_diagnostics_are_sanitized():
    error = checker.urllib.error.URLError("Authorization:Bearer ghp_secret123 token=ghp_secret123")
    with patch.object(checker.urllib.request, "urlopen", side_effect=error), pytest.raises(checker.CompatibilityError) as raised:
        checker.fetch_workflow("org/repo", ".github/workflows/codex-execute.yml", "main", "ghp_secret123")
    message = str(raised.value)
    assert "ghp_secret123" not in message
    assert "Authorization" not in message or "[redacted]" in message


def test_migrated_target_entries_use_v2_and_expected_paths():
    entries = checker.load_registry(ROOT / "config/codex-repositories.json")
    assert entries["Young-Consultations/slugger"]["contract_version"] == checker.CANONICAL_VERSION
    assert entries["Young-Consultations/consulting-playbook"]["contract_version"] == checker.CANONICAL_VERSION
    assert all(
        item["workflow_ref"].endswith("@codex-adapter-v2.3.1")
        for item in entries.values()
    )
    assert all(
        item["conformance"]["adapter_ref"] == "codex-adapter-v2.3.1"
        and item["conformance"]["status"] == "pass"
        and item["conformance"]["activation_evidence_sufficient"] is True
        for item in entries.values()
    )
