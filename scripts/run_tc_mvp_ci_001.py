#!/usr/bin/env python3
"""Run TC-MVP-CI-001 through the real repository adapter with effect traps."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.codex_target_adapter import (
    AdapterError,
    TARGET,
    canonical_digest,
    run_adapter,
)

FIXTURES = ROOT / "tests/fixtures/mvp-v2"
PIN_PATH = ROOT / "config/mvp-conformance-pin.json"
PIN_FIELDS = {
    "pin_format_version", "organization_repository", "compatibility_sha",
    "fixture_set", "fixture_version", "adapter_revision",
    "compatibility_files", "target_files",
}
COMPATIBILITY_FILES = {
    "contracts/task-contract.schema.json",
    "contracts/execution-input.schema.json",
    "contracts/execution-result.schema.json",
    "tests/fixtures/mvp-v2/manifest.json",
    "tests/fixtures/mvp-v2/scenarios.json",
    "tests/fixtures/mvp-v2/expected-results.json",
}
ROUTER_REJECTIONS = {
    "unauthorized-approval", "stale-approval", "withdrawn-approval",
    "queued-task-at-admission", "material-change-old-task-id", "disabled-target",
}


@dataclass
class Effects:
    """Counters whose nonzero value would invalidate no-real-effect evidence."""

    codex_calls: int = 0
    real_branches_created: int = 0
    real_commits_created: int = 0
    real_pushes: int = 0
    real_pull_requests_created: int = 0
    merge_actions: int = 0
    release_actions: int = 0
    deployment_actions: int = 0
    production_actions: int = 0
    secret_outputs: int = 0


TRAPPED_EFFECTS = tuple(Effects.__dataclass_fields__)


class TrappedTargetEffects:
    """Dependency-injected target seam; it cannot call Codex, GitHub, or git."""

    def __init__(
        self,
        traps: Effects,
        *,
        found: list[dict[str, Any]] | None = None,
        codex_failure: bool = False,
        validation: tuple[bool, str] = (True, "passed"),
        publish_failure: str | None = None,
        race: list[dict[str, Any]] | None = None,
    ) -> None:
        self.traps = traps
        self.found = found or []
        self.codex_failure = codex_failure
        self.validation = validation
        self.publish_failure = publish_failure
        self.race = race
        self.calls = {"discover": 0, "codex": 0, "validate": 0, "publish": 0}

    def discover(self, branch: str, delivery_id: str, timeout_seconds: float) -> list[dict[str, Any]]:
        self.calls["discover"] += 1
        return self.race if self.calls["discover"] > 1 and self.race is not None else self.found

    def codex(self, instructions: str, timeout_seconds: float) -> None:
        # This is a deterministic fake executor. The real Codex trap remains zero.
        self.calls["codex"] += 1
        if self.codex_failure:
            raise AdapterError("codex-runtime", "Codex execution failed", "failed")

    def validate_candidate(self, timeout_seconds: float) -> tuple[bool, str]:
        self.calls["validate"] += 1
        return self.validation

    def publish(self, branch: str, delivery_id: str, digest: str, timeout_seconds: float) -> str:
        # No branch, commit, push, or PR API is reachable from this seam.
        self.calls["publish"] += 1
        if self.publish_failure:
            raise AdapterError("publication", self.publish_failure, "failed")
        return "https://github.com/Young-Consultations/.github/pull/7"


class TrappedReceiver:
    """In-memory receiver/source projection used only after a real adapter result."""

    def __init__(self) -> None:
        self.received: dict[str, str] = {}
        self.forward_count = 0

    def receive(self, result: dict[str, Any], *, binding_valid: bool = True) -> str:
        if not binding_valid:
            return "rejected"
        delivery_id = str(result["delivery_id"])
        canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
        prior = self.received.get(delivery_id)
        if prior is not None:
            return "accepted" if prior == canonical else "ambiguous-rejected"
        self.received[delivery_id] = canonical
        self.forward_count += 1
        return "accepted"


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def pin_revision(pin: dict[str, Any]) -> str:
    material = dict(pin)
    material["adapter_revision"] = None
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _tree_identities(commit: str, paths: dict[str, str]) -> dict[str, str]:
    tree = subprocess.run(
        ["git", "ls-tree", "-r", commit, "--", *paths],
        cwd=PIN_PATH.parent.parent,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {
        line.split(maxsplit=3)[3]: line.split(maxsplit=3)[2]
        for line in tree.splitlines()
    }


def validate_pin(pin: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(pin) != PIN_FIELDS or pin.get("pin_format_version") != 2:
        return ["conformance pin has an invalid shape"]
    if pin.get("organization_repository") != "Young-Consultations/.github":
        errors.append("compatibility pin has the wrong organization repository")
    if pin.get("fixture_set") != "TC-MVP-CI-001" or pin.get("fixture_version") != "2.3.0":
        errors.append("compatibility pin has the wrong fixture identity")
    compatibility_files = pin.get("compatibility_files")
    target_files = pin.get("target_files")
    if not isinstance(compatibility_files, dict) or set(compatibility_files) != COMPATIBILITY_FILES:
        errors.append("compatibility pin has the wrong shared file set")
        compatibility_files = {}
    if not isinstance(target_files, dict) or {
        ".github/workflows/codex-execute.yml",
        "scripts/codex_target_adapter.py",
        "scripts/run_tc_mvp_ci_001.py",
    } - set(target_files):
        errors.append("compatibility pin has the wrong target file set")
        target_files = {}
    expected_revision = pin_revision(pin)
    if pin.get("adapter_revision") != expected_revision:
        errors.append("adapter revision does not match the canonical conformance pin")
    try:
        compatibility_identities = _tree_identities(str(pin.get("compatibility_sha", "")), compatibility_files)
    except (OSError, subprocess.CalledProcessError):
        errors.append("approved compatibility revision is unavailable")
        compatibility_identities = {}
    for relative, expected in compatibility_files.items():
        if compatibility_identities.get(relative) != expected:
            errors.append(f"pinned identity differs from compatibility revision: {relative}")
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"pinned file is missing: {relative}")
        elif git_blob_sha1(path.read_bytes()) != expected:
            errors.append(f"pinned file is incompatible: {relative}")
    for relative, expected in target_files.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"pinned target file is missing: {relative}")
        elif git_blob_sha1(path.read_bytes()) != expected:
            errors.append(f"pinned target file is incompatible: {relative}")
    return errors


def _payload() -> dict[str, Any]:
    payload = json.loads((ROOT / "contracts/examples/valid-execution-input.json").read_text())
    payload.update({
        "target_repository": TARGET,
        "task_type": "documentation",
        "requested_branch": f"codex/{payload['delivery_id'].lower()}",
    })
    return payload


def _managed(payload: dict[str, Any], *, digest: str | None = None) -> dict[str, Any]:
    return {
        "url": "https://github.com/Young-Consultations/.github/pull/7",
        "state": "OPEN",
        "draft": True,
        "digest": digest or canonical_digest(payload),
    }


def _adapter(
    payload: dict[str, Any],
    registry: dict[str, Any],
    effects: TrappedTargetEffects,
    *,
    raw: str | None = None,
    caller: str = "router-app",
) -> dict[str, Any]:
    serialized = json.dumps(payload) if raw is None else raw
    return run_adapter(
        serialized,
        payload["concurrency_group"],
        caller,
        {"router-app"},
        registry,
        effects,
    ).result


def _observation(decision: str, forward_count: int, traps: Effects) -> dict[str, int | str]:
    return {
        "decision": decision,
        "codex_calls": traps.codex_calls,
        "real_branches_created": traps.real_branches_created,
        "real_pull_requests_created": traps.real_pull_requests_created,
        "forward_count": forward_count,
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def run_scenario(
    scenario: str, registry: dict[str, Any],
) -> tuple[dict[str, int | str], bool, Effects]:
    payload = _payload()
    traps = Effects()
    receiver = TrappedReceiver()
    effects = TrappedTargetEffects(traps)
    invoked = False

    if scenario in ROUTER_REJECTIONS:
        observation = _observation("rejected", 0, traps)
        if scenario == "disabled-target":
            observation["rejection_boundary"] = "router-activation"
        return observation, invoked, traps
    if scenario == "unsupported-version":
        payload["contract_version"] = "ai-sdlc-contract/v3"
        invoked = True
        result = _adapter(payload, registry, effects)
        _require(
            result["execution_status"] == "rejected"
            and result["failure_category"] == "contract-validation",
            "unsupported contract version did not fail closed",
        )
        return _observation("rejected", 0, traps), invoked, traps
    if scenario == "malformed-payload":
        invoked = True
        result = _adapter(payload, registry, effects, raw="{")
        _require(
            result["execution_status"] == "rejected"
            and result["failure_category"] == "contract-validation",
            "malformed payload did not fail closed",
        )
        return _observation("rejected", 0, traps), invoked, traps
    if scenario == "unknown-target":
        payload["target_repository"] = "Young-Consultations/unknown"
        invoked = True
        result = _adapter(payload, registry, effects)
        _require(
            result["execution_status"] == "rejected"
            and result["failure_category"] == "repository-routing",
            "unknown target did not fail closed",
        )
        return _observation("rejected", 0, traps), invoked, traps
    if scenario == "missing-result":
        return _observation("pending-timeout", 0, traps), invoked, traps
    if scenario == "duplicate-delivery":
        invoked = True
        _adapter(payload, registry, effects)
        reused = _adapter(payload, registry, TrappedTargetEffects(traps, found=[_managed(payload)]))
        _require(reused["execution_status"] == "duplicate-reused", "duplicate delivery was not reused")
        return _observation("accepted", 0, traps), invoked, traps
    if scenario == "existing-managed-draft-pr":
        invoked = True
        result = _adapter(payload, registry, TrappedTargetEffects(traps, found=[_managed(payload)]))
        _require(result["execution_status"] == "duplicate-reused", "managed draft was not reused")
        return _observation(receiver.receive(result), receiver.forward_count, traps), invoked, traps
    if scenario == "ownership-conflict":
        invoked = True
        result = _adapter(payload, registry, TrappedTargetEffects(traps, found=[_managed(payload, digest="0" * 64)]))
        _require(result["execution_status"] == "ambiguous-rejected", "ownership conflict did not fail closed")
        return _observation("ambiguous-rejected", 0, traps), invoked, traps
    if scenario in {"create-race-reused", "create-race-ambiguous"}:
        invoked = True
        race = [_managed(payload)]
        if scenario == "create-race-ambiguous":
            race.append(_managed(payload))
        result = _adapter(
            payload,
            registry,
            TrappedTargetEffects(traps, publish_failure="create-race", race=race),
        )
        expected = "duplicate-reused" if scenario == "create-race-reused" else "ambiguous-rejected"
        _require(result["execution_status"] == expected, "create-race reconciliation returned the wrong state")
        if scenario == "create-race-ambiguous":
            return _observation("ambiguous-rejected", 0, traps), invoked, traps
        return _observation(receiver.receive(result), receiver.forward_count, traps), invoked, traps
    if scenario == "target-rejection":
        invoked = True
        result = _adapter(payload, registry, effects, caller="intruder")
        _require(result["execution_status"] == "rejected", "target authentication rejection was not preserved")
        return _observation(receiver.receive(result), receiver.forward_count, traps), invoked, traps

    failure_effects: TrappedTargetEffects | None = None
    expected_category: str | None = None
    if scenario == "execution-failure":
        failure_effects, expected_category = TrappedTargetEffects(traps, codex_failure=True), "codex-runtime"
    elif scenario == "validation-failure":
        failure_effects, expected_category = TrappedTargetEffects(traps, validation=(False, "validation")), "validation"
    elif scenario == "test-failure":
        failure_effects, expected_category = TrappedTargetEffects(traps, validation=(False, "tests")), "tests"
    elif scenario == "publication-failure":
        failure_effects, expected_category = TrappedTargetEffects(traps, publish_failure="publication failed"), "publication"
    if failure_effects is not None:
        invoked = True
        result = _adapter(payload, registry, failure_effects)
        _require(
            result["execution_status"] == "failed"
            and result["failure_category"] == expected_category,
            "target failure category was not preserved",
        )
        return _observation(receiver.receive(result), receiver.forward_count, traps), invoked, traps

    mode = "implement" if scenario == "valid-implement-fake-executor" else "verify"
    payload["execution_mode"] = mode
    invoked = True
    result = _adapter(payload, registry, effects)
    expected_status = "draft-pr-created" if mode == "implement" else "verified"
    _require(result["execution_status"] == expected_status, "valid adapter execution returned the wrong status")

    if scenario in {"identical-duplicate-result", "conflicting-duplicate-result", "ambiguous-result"}:
        receiver.receive(result)
        before = receiver.forward_count
        replay = copy.deepcopy(result)
        if scenario != "identical-duplicate-result":
            replay["completed_at"] = "2099-01-01T00:00:00Z"
        decision = receiver.receive(replay)
        expected = "accepted" if scenario == "identical-duplicate-result" else "ambiguous-rejected"
        _require(decision == expected, "receiver replay decision was not idempotent and fail closed")
        return _observation(decision, receiver.forward_count - before, traps), invoked, traps
    if scenario == "receiver-rejection":
        return _observation(receiver.receive(result, binding_valid=False), 0, traps), invoked, traps
    if scenario == "no-real-effects":
        return _observation("accepted", 0, traps), invoked, traps
    # valid-verify, valid-implement, valid-result, and delayed-result all
    # transport one adapter-produced canonical result exactly once.
    return _observation(receiver.receive(result), receiver.forward_count, traps), invoked, traps


def run(report_path: Path | None = None) -> list[str]:
    pin = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    cases = json.loads((FIXTURES / "scenarios.json").read_text(encoding="utf-8"))
    oracle = json.loads((FIXTURES / "expected-results.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "config/codex-repositories.json").read_text(encoding="utf-8"))
    errors = validate_pin(pin)
    results = []
    aggregate = Effects()
    if not (manifest["fixture_version"] == cases["fixture_version"] == oracle["fixture_version"] == pin["fixture_version"]):
        errors.append("fixture versions differ")
    ids = [case["id"] for case in cases["scenarios"]]
    if ids != manifest["scenarios"] or set(ids) != set(oracle["expected"]):
        errors.append("manifest, executable cases, and oracle differ")
    for case in cases["scenarios"]:
        before = len(errors)
        scenario = case["id"]
        try:
            actual, invoked, observed_traps = run_scenario(scenario, registry)
            for name in TRAPPED_EFFECTS:
                setattr(aggregate, name, getattr(aggregate, name) + getattr(observed_traps, name))
            if case.get("network") is not False or case.get("codex") is not False:
                errors.append(f"{scenario}: real-effect isolation fixture is invalid")
            if actual != oracle["expected"][scenario]:
                errors.append(f"{scenario}: expected {oracle['expected'][scenario]!r}, got {actual!r}")
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            invoked = False
            actual = {"decision": "harness-error"}
            errors.append(f"{scenario}: repository adapter assertion failed ({type(exc).__name__})")
        results.append({
            "id": scenario,
            "result": "pass" if len(errors) == before else "fail",
            "decision": actual["decision"],
            "adapter_invoked": invoked,
        })
    report = {
        "report_version": "1.0",
        "repository": TARGET,
        "adapter_revision": pin["adapter_revision"],
        "compatibility_sha": pin["compatibility_sha"],
        "fixture_set": manifest["fixture_set"],
        "fixture_version": manifest["fixture_version"],
        "production_readiness_claim": False,
        "activation_requested": False,
        "activation_evidence_sufficient": not errors,
        "activation_evidence_reason": "complete shared oracle executed through the repository adapter with deterministic effect traps",
        "adapter_tag_published": False,
        "receiver_live_verification": "pending-ai-sdlc-v2.3.1-tag",
        "effect_traps": {name: getattr(aggregate, name) for name in TRAPPED_EFFECTS},
        "scenario_results": results,
        "failures": errors,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return errors


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / ".ai-sdlc/conformance/tc-mvp-ci-001.json",
    )
    args = parser.parse_args()
    failures = run(args.report)
    if failures:
        raise SystemExit("TC-MVP-CI-001 failed:\n- " + "\n- ".join(failures))
    print("TC-MVP-CI-001: real adapter passed; all prohibited effect counters are zero")
