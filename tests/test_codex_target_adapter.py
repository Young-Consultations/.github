import copy
import json
import subprocess
from pathlib import Path

import pytest

from scripts.codex_target_adapter import AdapterError, GitHubEffects, TARGET, canonical_digest, run_adapter

ROOT = Path(__file__).parents[1]


class FakeEffects:
    def __init__(self, *, found=None, codex_failure=False, validation=(True, "passed"), publish_failure=None, race=None,
                 exception_phase=None, exception=None):
        self.found = found or []
        self.codex_failure = codex_failure
        self.validation = validation
        self.publish_failure = publish_failure
        self.race = race
        self.exception_phase = exception_phase
        self.exception = exception or OSError("sensitive operational detail")
        self.calls = {"discover": 0, "codex": 0, "validate": 0, "publish": 0}
        self.timeouts = {}

    def discover(self, branch, delivery_id, timeout_seconds):
        self.calls["discover"] += 1
        self.timeouts["discover"] = timeout_seconds
        if self.exception_phase == "discover":
            raise self.exception
        if self.calls["discover"] > 1 and self.race is not None:
            return self.race
        return self.found

    def codex(self, instructions, timeout_seconds):
        self.calls["codex"] += 1
        self.timeouts["codex"] = timeout_seconds
        if self.exception_phase == "codex":
            raise self.exception
        if self.codex_failure:
            raise AdapterError("codex-runtime", "Codex execution failed", "failed")

    def validate_candidate(self, timeout_seconds):
        self.calls["validate"] += 1
        self.timeouts["validate"] = timeout_seconds
        if self.exception_phase == "validation":
            raise self.exception
        return self.validation

    def publish(self, branch, delivery_id, digest, timeout_seconds):
        self.calls["publish"] += 1
        self.timeouts["publish"] = timeout_seconds
        if self.exception_phase == "publish":
            raise self.exception
        if self.publish_failure:
            raise AdapterError("publication", self.publish_failure, "failed")
        return "https://github.com/Young-Consultations/.github/pull/7"


@pytest.fixture
def payload():
    value = json.loads((ROOT / "contracts/examples/valid-execution-input.json").read_text())
    value.update({
        "target_repository": TARGET,
        "task_type": "documentation",
        "requested_branch": f"codex/{value['delivery_id'].lower()}",
    })
    return value


@pytest.fixture
def registry():
    return json.loads((ROOT / "config/codex-repositories.json").read_text())


def execute(payload, registry, effects=None, **overrides):
    payload = copy.deepcopy(payload)
    payload.update(overrides)
    effects = effects or FakeEffects()
    outcome = run_adapter(json.dumps(payload), payload["concurrency_group"], "router-app", {"router-app"}, registry, effects)
    return outcome.result, effects


def test_valid_verify_has_no_effects(payload, registry):
    result, effects = execute(payload, registry, execution_mode="verify")
    assert result["execution_status"] == "verified"
    assert result["branch_name"] is result["pull_request_url"] is None
    assert effects.calls == {"discover": 1, "codex": 0, "validate": 0, "publish": 0}


def test_fake_implement(payload, registry):
    result, effects = execute(payload, registry, execution_mode="implement")
    assert result["execution_status"] == "draft-pr-created"
    assert result["delivery_id"] == payload["delivery_id"]
    assert effects.calls == {"discover": 1, "codex": 1, "validate": 1, "publish": 1}


@pytest.mark.parametrize("mutation,category", [
    ({"target_repository": "Young-Consultations/slugger"}, "repository-routing"),
    ({"contract_version": "ai-sdlc-contract/v3"}, "contract-validation"),
    ({"task_type": "security"}, "authorization"),
    ({"draft_pr_only": False}, "contract-validation"),
])
def test_rejected_policy_paths_have_no_effects(payload, registry, mutation, category):
    result, effects = execute(payload, registry, **mutation)
    assert result["failure_category"] == category
    assert effects.calls["codex"] == effects.calls["publish"] == 0


def test_historical_activation_metadata_does_not_block_adapter(payload, registry):
    # Older compatibility snapshots may contain the former field.  It is not
    # target-side authorization and therefore cannot invalidate a dispatch.
    registry["repositories"][TARGET]["enabled"] = False
    result, effects = execute(payload, registry)
    assert result["execution_status"] == "draft-pr-created"
    assert effects.calls == {"discover": 1, "codex": 1, "validate": 1, "publish": 1}


def test_missing_target_identity_is_rejected(payload, registry):
    del registry["repositories"][TARGET]
    result, effects = execute(payload, registry)
    assert result["failure_category"] == "repository-routing"
    assert effects.calls["codex"] == 0


def test_malformed_input_and_unauthorized_caller(payload, registry):
    effects = FakeEffects()
    malformed = run_adapter("{", payload["concurrency_group"], "router-app", {"router-app"}, registry, effects).result
    unauthorized = run_adapter(json.dumps(payload), payload["concurrency_group"], "intruder", {"router-app"}, registry, effects).result
    assert malformed["failure_category"] == "contract-validation"
    assert unauthorized["failure_category"] == "authentication"
    assert effects.calls["codex"] == 0


@pytest.mark.parametrize("field,value,fallback", [
    ("correlation_id", "bad identity!", "rejected-correlation"),
    ("delivery_id", "x" * 129, "rejected-delivery"),
    ("target_repository", "not-a-repository", TARGET),
])
def test_malformed_identity_produces_schema_valid_canonical_rejection(payload, registry, field, value, fallback):
    payload[field] = value
    effects = FakeEffects()
    outcome = run_adapter(json.dumps(payload), payload["concurrency_group"], "router-app", {"router-app"}, registry, effects)
    result = outcome.result
    assert result["execution_status"] == "rejected"
    assert result[field] == fallback
    assert value not in json.dumps(result)
    assert outcome.source_issue == payload["source_issue"]  # report routing remains available
    assert effects.calls == {"discover": 0, "codex": 0, "validate": 0, "publish": 0}


def test_invalid_transport_concurrency_group(payload, registry):
    effects = FakeEffects()
    result = run_adapter(json.dumps(payload), "different/group", "router-app", {"router-app"}, registry, effects).result
    assert result["failure_category"] == "contract-validation"
    assert effects.calls["discover"] == 0


def managed(payload, **updates):
    value = {"url": "https://github.com/Young-Consultations/.github/pull/4", "state": "OPEN", "draft": True,
             "digest": canonical_digest(payload)}
    value.update(updates)
    return value


def test_duplicate_matching_delivery_is_reused(payload, registry):
    effects = FakeEffects(found=[managed(payload)])
    result, effects = execute(payload, registry, effects)
    assert result["execution_status"] == "duplicate-reused"
    assert effects.calls["codex"] == effects.calls["publish"] == 0


def test_changed_payload_and_ambiguous_ownership_fail_closed(payload, registry):
    changed, _ = execute(payload, registry, FakeEffects(found=[managed(payload, digest="0" * 64)]))
    ambiguous, _ = execute(payload, registry, FakeEffects(found=[managed(payload), managed(payload)]))
    assert changed["execution_status"] == ambiguous["execution_status"] == "ambiguous-rejected"


def test_create_race_requeries_and_converges(payload, registry):
    effects = FakeEffects(publish_failure="create-race", race=[managed(payload)])
    result, effects = execute(payload, registry, effects)
    assert result["execution_status"] == "duplicate-reused"
    assert effects.calls["discover"] == 2


def test_publish_retries_pr_creation_from_pushed_commit(monkeypatch):
    effects = GitHubEffects()
    gh_calls = []

    monkeypatch.setenv("TARGET_PUBLICATION_TOKEN", "test-token")

    def git_run(command, **kwargs):
        returncode = 1 if command[1:4] == ["diff", "--cached", "--quiet"] else 0
        return type("Result", (), {"returncode": returncode})()

    monkeypatch.setattr("scripts.codex_target_adapter.subprocess.run", git_run)

    def create_pr(*args, **kwargs):
        gh_calls.append(args)
        if len(gh_calls) < 3:
            raise subprocess.CalledProcessError(1, args)
        return "https://github.com/Young-Consultations/.github/pull/7\n"

    monkeypatch.setattr(effects, "_gh", create_pr)

    assert effects.publish("codex/delivery", "delivery", "0" * 64, 60).endswith("/pull/7")
    assert len(gh_calls) == 3
    assert all(call[:2] == ("pr", "create") for call in gh_calls)


@pytest.mark.parametrize("effects,category", [
    (FakeEffects(codex_failure=True), "codex-runtime"),
    (FakeEffects(validation=(False, "validation")), "validation"),
    (FakeEffects(validation=(False, "tests")), "tests"),
    (FakeEffects(publish_failure="publication failed"), "publication"),
])
def test_terminal_implement_failures(payload, registry, effects, category):
    result, effects = execute(payload, registry, effects)
    assert result["execution_status"] == "failed"
    assert result["failure_category"] == category
    assert result["pull_request_url"] is None


@pytest.mark.parametrize("phase,exception,category", [
    ("discover", subprocess.CalledProcessError(1, ["gh", "secret"]), "dependency"),
    ("discover", KeyError("TARGET_PUBLICATION_TOKEN"), "authentication"),
    ("codex", OSError("secret path"), "codex-runtime"),
    ("validation", OSError("secret path"), "validation"),
    ("publish", OSError("secret path"), "publication"),
    ("publish", FileNotFoundError("gh"), "dependency"),
])
def test_effect_exceptions_become_redacted_canonical_failures(payload, registry, phase, exception, category):
    result, _ = execute(payload, registry, FakeEffects(exception_phase=phase, exception=exception))
    assert result["execution_status"] == "failed"
    assert result["failure_category"] == category
    assert "secret" not in result["failure_message"]
    if phase == "validation":
        assert result["validation_result"] == "failed"


def test_timeout_is_canonical_and_prevents_publication(payload, registry):
    effects = FakeEffects(exception_phase="codex", exception=subprocess.TimeoutExpired(["codex"], 60))
    result, effects = execute(payload, registry, effects, timeout_minutes=1)
    assert result["execution_status"] == "failed"
    assert result["failure_category"] == "timeout"
    assert effects.calls == {"discover": 1, "codex": 1, "validate": 0, "publish": 0}


def test_remaining_deadline_is_propagated_to_every_effect(payload, registry):
    effects = FakeEffects()
    result, effects = execute(payload, registry, effects, timeout_minutes=1)
    assert result["execution_status"] == "draft-pr-created"
    assert set(effects.timeouts) == {"discover", "codex", "validate", "publish"}
    assert all(0 < timeout <= 60 for timeout in effects.timeouts.values())


def test_github_codex_effect_applies_timeout_and_cleans_instruction_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    observed = {}

    def expire(*args, **kwargs):
        observed.update(kwargs)
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr("scripts.codex_target_adapter.subprocess.run", expire)
    with pytest.raises(subprocess.TimeoutExpired):
        GitHubEffects().codex("do not disclose", 12.5)
    assert observed["timeout"] == 12.5
    assert not (tmp_path / ".codex-instructions.txt").exists()


@pytest.mark.parametrize("phase,validation,test", [
    ("validation", "failed", "not-run"),
    ("tests", "passed", "failed"),
])
def test_failed_candidate_phase_status_is_preserved(payload, registry, phase, validation, test):
    result, _ = execute(payload, registry, FakeEffects(validation=(False, phase)))
    assert result["validation_result"] == validation
    assert result["test_result"] == test


def test_identity_is_delivery_not_transport_or_observability(payload, registry):
    payload["correlation_id"] = "different-correlation"
    payload["concurrency_group"] = "transport-only"
    result, _ = execute(payload, registry)
    assert result["branch_name"] == f"codex/{payload['delivery_id'].lower()}"
