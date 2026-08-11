import copy
import json
from pathlib import Path

import pytest

from scripts.codex_target_adapter import AdapterError, TARGET, canonical_digest, run_adapter

ROOT = Path(__file__).parents[1]


class FakeEffects:
    def __init__(self, *, found=None, codex_failure=False, validation=(True, "passed"), publish_failure=None, race=None):
        self.found = found or []
        self.codex_failure = codex_failure
        self.validation = validation
        self.publish_failure = publish_failure
        self.race = race
        self.calls = {"discover": 0, "codex": 0, "validate": 0, "publish": 0}

    def discover(self, branch, delivery_id):
        self.calls["discover"] += 1
        if self.calls["discover"] > 1 and self.race is not None:
            return self.race
        return self.found

    def codex(self, instructions):
        self.calls["codex"] += 1
        if self.codex_failure:
            raise AdapterError("codex-runtime", "Codex execution failed", "failed")

    def validate_candidate(self):
        self.calls["validate"] += 1
        return self.validation

    def publish(self, branch, delivery_id, digest):
        self.calls["publish"] += 1
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
    value = json.loads((ROOT / "config/codex-repositories.json").read_text())
    value["repositories"][TARGET]["enabled"] = True
    return value


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


def test_disabled_target(payload, registry):
    registry["repositories"][TARGET]["enabled"] = False
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


def test_identity_is_delivery_not_transport_or_observability(payload, registry):
    payload["correlation_id"] = "different-correlation"
    payload["concurrency_group"] = "transport-only"
    result, _ = execute(payload, registry)
    assert result["branch_name"] == f"codex/{payload['delivery_id'].lower()}"
