#!/usr/bin/env python3
"""TC-MVP-E2E-001 dual-mode acceptance harness.

SIM exercises the control-plane router admission/construction path, the enabled
target's immutable adapter, and the candidate receiver through deterministic
fake external effects. REAL is a fail-closed readiness check and never invokes
Codex or mutates GitHub here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import codex_router
from scripts.codex_result_receiver import ADMISSION, JournalComment, ReceiverError, marker, receive
from scripts.validate_release import validate as validate_release

ACTIVATION = ROOT / "config/codex-activation.json"
REGISTRY = ROOT / "config/codex-repositories.json"
RELEASE_MANIFEST = ROOT / "release/release-manifest.json"
REAL_TARGET = "Young-Consultations/consulting-playbook"
PUBLISHED_BASELINE = "2.3.2"
CANDIDATE_RELEASE = "2.4.0"
TARGET_ROOT_ENV = "TC_MVP_E2E_TARGET_ROOT"


@dataclass
class EffectTraps:
    """Counters for prohibited real effects. They must remain zero."""

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


@dataclass
class FakeEffectCounts:
    """Observable deterministic calls through the fake target effect seam."""

    discover_calls: int = 0
    codex_calls: int = 0
    validation_calls: int = 0
    publication_calls: int = 0


TRAPPED_EFFECTS = tuple(EffectTraps.__dataclass_fields__)
FAKE_EFFECT_FIELDS = tuple(FakeEffectCounts.__dataclass_fields__)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_output(args: list[str], cwd: Path = ROOT) -> tuple[str | None, str | None]:
    try:
        value = subprocess.check_output(
            ["git", *args], cwd=cwd, text=True, stderr=subprocess.STDOUT
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "output", "") or str(exc)
        return None, " ".join(str(detail).split())[:300]
    return value, None


def _control_plane_commit() -> str | None:
    value, _ = _git_output(["rev-parse", "HEAD"])
    return value


def _candidate_release_errors() -> list[str]:
    manifest = _load(RELEASE_MANIFEST)
    errors = list(validate_release(ROOT))
    if str(manifest.get("release_version")) != CANDIDATE_RELEASE:
        errors.append(f"expected release candidate {CANDIDATE_RELEASE}")
    if manifest.get("tag") != f"ai-sdlc-v{CANDIDATE_RELEASE}":
        errors.append("release candidate tag does not match candidate version")
    return errors


def _control_plane_release_identity_errors() -> list[str]:
    """Require REAL preflight to execute from the immutable published tag."""

    tag = f"ai-sdlc-v{CANDIDATE_RELEASE}"
    head, head_error = _git_output(["rev-parse", "HEAD"])
    if head_error:
        return [f"control-plane checkout identity cannot be read: {head_error}"]
    tag_commit, tag_error = _git_output(["rev-list", "-n", "1", tag])
    if tag_error or not tag_commit:
        return [f"published tag {tag} is not available in this checkout"]
    if head != tag_commit:
        return [f"REAL preflight must execute from {tag} commit {tag_commit}, got {head}"]
    return []


def _real_release_errors() -> list[str]:
    errors = list(validate_release(ROOT, require_publishable=True))
    manifest = _load(RELEASE_MANIFEST)
    if manifest.get("tag_published") is not True:
        message = f"ai-sdlc-v{CANDIDATE_RELEASE} is not published; REAL remains blocked"
        if message not in errors:
            errors.append(message)
    errors.extend(_control_plane_release_identity_errors())
    return errors


def _activation_errors() -> list[str]:
    activation = _load(ACTIVATION).get("targets", {})
    enabled = sorted(name for name, value in activation.items() if value is True)
    return [] if enabled == [REAL_TARGET] else [
        f"expected sole enabled target {REAL_TARGET}, got {enabled}"
    ]


def _target_root() -> Path:
    raw = os.environ.get(TARGET_ROOT_ENV)
    return Path(raw).resolve() if raw else ROOT


def _load_target_adapter(target_root: Path) -> ModuleType:
    path = target_root / "scripts/codex_target_adapter.py"
    if not path.is_file():
        raise FileNotFoundError(f"target adapter missing at {path}")
    spec = importlib.util.spec_from_file_location("tc_mvp_e2e_target_adapter", path)
    if spec is None or spec.loader is None:
        raise ImportError("target adapter could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _registry_entry() -> dict[str, Any]:
    entry = _load(REGISTRY).get("repositories", {}).get(REAL_TARGET)
    if not isinstance(entry, dict):
        raise ValueError("enabled target is missing from registry")
    return entry


def _target_identity_errors(target_root: Path) -> list[str]:
    expected = _registry_entry().get("conformance", {}).get("adapter_commit_sha")
    if not isinstance(expected, str) or len(expected) != 40:
        return ["registry target adapter commit is missing or invalid"]
    if not (target_root / ".git").exists():
        return ["target checkout is not a Git repository"]
    actual, error = _git_output(["rev-parse", "HEAD"], target_root)
    if error:
        return [f"target checkout identity cannot be read: {error}"]
    return [] if actual == expected else [
        f"target checkout {actual} does not match registry adapter commit {expected}"
    ]


def _target_receiver_pin_errors(target_root: Path) -> list[str]:
    workflow = target_root / ".github/workflows/codex-execute.yml"
    if not workflow.is_file():
        return ["enabled target execution workflow is missing"]
    required = (
        "Young-Consultations/.github/.github/workflows/codex-result-receiver.yml@"
        f"ai-sdlc-v{CANDIDATE_RELEASE}"
    )
    source = workflow.read_text(encoding="utf-8")
    return [] if source.count(required) == 1 else [
        f"enabled target is not pinned to the ai-sdlc-v{CANDIDATE_RELEASE} receiver"
    ]


def _task() -> dict[str, Any]:
    task = _load(ROOT / "contracts/examples/valid-task.json")
    task.update({
        "status": "approved",
        "executor": "codex",
        "project": "consulting-playbook",
        "task_type": "documentation",
        "target_repository": REAL_TARGET,
        "dependencies": [],
    })
    return task


def _route_task(task: dict[str, Any]) -> dict[str, Any]:
    """Run production router admission/construction without external dispatch."""

    names = ("TASK_PAYLOAD", "EXECUTION_MODE", "GITHUB_OUTPUT")
    previous = {name: os.environ.get(name) for name in names}
    os.environ["TASK_PAYLOAD"] = json.dumps(task)
    os.environ["EXECUTION_MODE"] = "implement"
    os.environ["GITHUB_OUTPUT"] = os.devnull
    try:
        try:
            return codex_router.validate()
        except SystemExit as exc:
            raise ValueError(f"router admission failed with exit {exc.code}") from exc
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class FakeTargetEffects:
    """Target effect seam with no reachable real mutation APIs."""

    def __init__(
        self,
        adapter: ModuleType,
        traps: EffectTraps,
        *,
        found: list[dict[str, Any]] | None = None,
    ) -> None:
        self.adapter = adapter
        self.traps = traps
        self.found = found or []
        self.calls = FakeEffectCounts()

    def discover(self, branch: str, delivery_id: str, timeout_seconds: float) -> Any:
        self.calls.discover_calls += 1
        return self.adapter.Ownership(bool(self.found), self.found)

    def codex(self, instructions: str, timeout_seconds: float) -> None:
        self.calls.codex_calls += 1
        if not instructions:
            raise ValueError("instructions must not be empty")

    def validate_candidate(self, timeout_seconds: float) -> tuple[bool, str]:
        self.calls.validation_calls += 1
        return True, "passed"

    def publish(self, branch: str, delivery_id: str, digest: str, timeout_seconds: float) -> str:
        self.calls.publication_calls += 1
        return "https://github.com/Young-Consultations/consulting-playbook/pull/999999"


class SimJournal:
    """In-memory external-effect seam around the real receiver implementation."""

    def __init__(self, payload: dict[str, Any]) -> None:
        binding = {
            key: payload[key]
            for key in (
                "contract_version",
                "delivery_id",
                "correlation_id",
                "source_issue",
                "target_repository",
            )
        }
        self.entries = [JournalComment(marker(ADMISSION, binding), "router-bot")]
        self.projections: list[dict[str, Any]] = []

    def authenticate(self, repository: str) -> None:
        return None

    def comments(self, repository: str, issue: int) -> list[JournalComment]:
        return list(self.entries)

    def trusted_author(self, author: str, role: str) -> bool:
        return author == ("router-bot" if role == "admission" else "receiver-bot")

    def append(self, repository: str, issue: int, body: str) -> None:
        self.entries.append(JournalComment(body, "receiver-bot"))

    def forward(self, repository: str, projection: dict[str, Any]) -> None:
        self.projections.append(projection)


def _managed(adapter: ModuleType, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": "https://github.com/Young-Consultations/consulting-playbook/pull/999999",
        "state": "OPEN",
        "draft": True,
        "digest": adapter.canonical_digest(payload),
    }


def _run_target(adapter: ModuleType, payload: dict[str, Any], effects: FakeTargetEffects) -> dict[str, Any]:
    return adapter.run_adapter(
        json.dumps(payload), payload["concurrency_group"], "router-app", {"router-app"}, effects
    ).result


def _fake_counts(effects: FakeTargetEffects | None) -> dict[str, int]:
    if effects is None:
        return {name: 0 for name in FAKE_EFFECT_FIELDS}
    return {name: getattr(effects.calls, name) for name in FAKE_EFFECT_FIELDS}


def run_sim(report_path: Path, target_root: Path | None = None) -> list[str]:
    """Exercise router, immutable target adapter, and candidate receiver with fakes."""

    target_root = target_root or _target_root()
    identity_errors = _target_identity_errors(target_root)
    errors = _candidate_release_errors() + _activation_errors() + identity_errors
    traps = EffectTraps()
    journal: SimJournal | None = None
    task: dict[str, Any] = {}
    payload: dict[str, Any] = {}
    route: dict[str, Any] = {}
    result: dict[str, Any] = {}
    replay: dict[str, Any] = {}
    primary_effects: FakeTargetEffects | None = None
    replay_effects: FakeTargetEffects | None = None
    conflict_decision = "not-run"
    first_receipt = "not-run"
    replay_receipt_status = "not-run"

    # Target identity is a code-loading boundary. Never import target code when
    # the checkout is missing, unreadable, or different from the registry pin.
    if not identity_errors:
        try:
            task = _task()
            route = _route_task(task)
            payload = dict(route["execution_input"])
            if route.get("target_repository") != REAL_TARGET:
                errors.append("router did not select the enabled REAL target")
            if route.get("workflow_ref") != _registry_entry().get("workflow_ref"):
                errors.append("router workflow selection does not match registry")

            adapter = _load_target_adapter(target_root)
            if getattr(adapter, "TARGET", None) != REAL_TARGET:
                errors.append("loaded adapter does not identify the enabled target")

            journal = SimJournal(payload)
            primary_effects = FakeTargetEffects(adapter, traps)
            result = _run_target(adapter, payload, primary_effects)
            if result.get("execution_status") != "draft-pr-created":
                errors.append(f"SIM expected draft-pr-created, got {result.get('execution_status')}")
            primary_counts = _fake_counts(primary_effects)
            if primary_counts != {
                "discover_calls": 1,
                "codex_calls": 1,
                "validation_calls": 1,
                "publication_calls": 1,
            }:
                errors.append(f"SIM primary fake-effect calls are unexpected: {primary_counts}")

            receipt = receive(json.dumps(result), payload["source_issue"], REAL_TARGET, journal)
            first_receipt = "accepted" if receipt.accepted else "rejected"
            if not receipt.accepted or receipt.duplicate or len(journal.projections) != 1:
                errors.append("SIM receiver/source projection did not accept exactly once")

            replay_effects = FakeTargetEffects(adapter, traps, found=[_managed(adapter, payload)])
            replay = _run_target(adapter, payload, replay_effects)
            if replay.get("execution_status") != "duplicate-reused":
                errors.append("SIM duplicate delivery did not reuse managed draft")
            replay_counts = _fake_counts(replay_effects)
            if replay_counts != {
                "discover_calls": 1,
                "codex_calls": 0,
                "validation_calls": 0,
                "publication_calls": 0,
            }:
                errors.append(f"SIM retry invoked unexpected fake effects: {replay_counts}")

            replay_receipt = receive(json.dumps(replay), payload["source_issue"], REAL_TARGET, journal)
            replay_receipt_status = (
                "accepted-duplicate"
                if replay_receipt.accepted and replay_receipt.duplicate
                else "unexpected"
            )
            if not replay_receipt.accepted or not replay_receipt.duplicate or len(journal.projections) != 1:
                errors.append("SIM equivalent duplicate result was not an idempotent no-op")

            conflicting = dict(result)
            conflicting["pull_request_url"] = "https://github.com/Young-Consultations/consulting-playbook/pull/999998"
            try:
                receive(json.dumps(conflicting), payload["source_issue"], REAL_TARGET, journal)
            except ReceiverError as exc:
                conflict_decision = "ambiguous-rejected" if exc.ambiguous else "rejected-non-ambiguous"
                if not exc.ambiguous:
                    errors.append("SIM conflicting duplicate was rejected without ambiguity")
            else:
                conflict_decision = "accepted"
                errors.append("SIM conflicting duplicate result did not fail closed")
        except (FileNotFoundError, ImportError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"SIM harness error: {type(exc).__name__}: {exc}")

    effect_counts = {name: getattr(traps, name) for name in TRAPPED_EFFECTS}
    if any(effect_counts.values()):
        errors.append(f"SIM prohibited real effects observed: {effect_counts}")

    entry, manifest = _registry_entry(), _load(RELEASE_MANIFEST)
    report = {
        "test_id": "TC-MVP-E2E-001-SIM",
        "mode": "sim",
        "published_baseline": PUBLISHED_BASELINE,
        "candidate_release": CANDIDATE_RELEASE,
        "candidate_tag_published": manifest.get("tag_published") is True,
        "control_plane_commit": _control_plane_commit(),
        "task_id": task.get("task_id"),
        "source_issue": payload.get("source_issue") or task.get("source_issue"),
        "delivery_id": payload.get("delivery_id"),
        "correlation_id": payload.get("correlation_id"),
        "target": REAL_TARGET,
        "router_validation_result": route.get("validation_result"),
        "router_workflow_ref": route.get("workflow_ref"),
        "dispatch_provider": "fake-in-process-target",
        "target_adapter_commit": entry["conformance"]["adapter_commit_sha"],
        "execution_provider": "fake",
        "shared_router_path": True,
        "shared_target_adapter_path": True,
        "shared_receiver_path": True,
        "sim_passed": not errors,
        "real_acceptance_satisfied": False,
        "primary_execution_status": result.get("execution_status"),
        "duplicate_execution_status": replay.get("execution_status"),
        "first_receiver_receipt": first_receipt,
        "duplicate_receiver_receipt": replay_receipt_status,
        "receiver_forward_count": len(journal.projections) if journal is not None else 0,
        "conflicting_duplicate_result": conflict_decision,
        "primary_fake_effect_calls": _fake_counts(primary_effects),
        "duplicate_fake_effect_calls": _fake_counts(replay_effects),
        "effect_traps": effect_counts,
        "failures": errors,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return errors


def _sim_evidence_errors(sim: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if (
        sim.get("test_id") != "TC-MVP-E2E-001-SIM"
        or sim.get("mode") != "sim"
        or sim.get("sim_passed") is not True
        or sim.get("failures") != []
    ):
        errors.append("SIM evidence is not a passing TC-MVP-E2E-001-SIM report")
    if sim.get("real_acceptance_satisfied") is not False:
        errors.append("SIM evidence incorrectly claims REAL acceptance")
    if not all(
        sim.get(field) is True
        for field in ("shared_router_path", "shared_target_adapter_path", "shared_receiver_path")
    ):
        errors.append("SIM evidence did not exercise the shared router, target, and receiver paths")
    if sim.get("execution_provider") != "fake" or sim.get("dispatch_provider") != "fake-in-process-target":
        errors.append("SIM evidence did not use the deterministic fake effect boundary")
    effect_traps = sim.get("effect_traps")
    if (
        not isinstance(effect_traps, dict)
        or set(effect_traps) != set(TRAPPED_EFFECTS)
        or any(value != 0 for value in effect_traps.values())
    ):
        errors.append("SIM evidence does not prove zero prohibited real effects")
    if sim.get("primary_fake_effect_calls") != {
        "discover_calls": 1,
        "codex_calls": 1,
        "validation_calls": 1,
        "publication_calls": 1,
    }:
        errors.append("SIM evidence does not prove the expected primary fake effects")
    if sim.get("duplicate_fake_effect_calls") != {
        "discover_calls": 1,
        "codex_calls": 0,
        "validation_calls": 0,
        "publication_calls": 0,
    }:
        errors.append("SIM evidence does not prove retry idempotency")
    if (
        sim.get("primary_execution_status") != "draft-pr-created"
        or sim.get("duplicate_execution_status") != "duplicate-reused"
        or sim.get("conflicting_duplicate_result") != "ambiguous-rejected"
        or sim.get("receiver_forward_count") != 1
    ):
        errors.append("SIM evidence is missing required result/receiver assertions")
    return errors


def run_real_preflight(sim_report_path: Path, target_root: Path | None = None) -> list[str]:
    """Fail closed until the corrected receiver is published and target-pinned."""

    target_root = target_root or _target_root()
    errors = (
        _real_release_errors()
        + _activation_errors()
        + _target_identity_errors(target_root)
        + _target_receiver_pin_errors(target_root)
    )
    if not sim_report_path.is_file():
        return errors + ["SIM evidence is missing"]

    sim = _load(sim_report_path)
    errors.extend(_sim_evidence_errors(sim))
    entry = _registry_entry()
    current_commit = _control_plane_commit()
    if (
        sim.get("target") != REAL_TARGET
        or sim.get("candidate_release") != CANDIDATE_RELEASE
        or sim.get("candidate_tag_published") is not True
        or sim.get("target_adapter_commit") != entry["conformance"]["adapter_commit_sha"]
        or sim.get("control_plane_commit") != current_commit
    ):
        errors.append(
            "SIM evidence does not match current published control plane/REAL target/candidate/adapter"
        )
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("sim", "real-preflight"), required=True)
    parser.add_argument("--target-root", type=Path, default=None)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / ".ai-sdlc/acceptance/tc-mvp-e2e-001-sim.json",
    )
    parser.add_argument(
        "--sim-report",
        type=Path,
        default=ROOT / ".ai-sdlc/acceptance/tc-mvp-e2e-001-sim.json",
    )
    args = parser.parse_args()
    target_root = args.target_root.resolve() if args.target_root else None
    failures = (
        run_sim(args.report, target_root)
        if args.mode == "sim"
        else run_real_preflight(args.sim_report, target_root)
    )
    if failures:
        raise SystemExit("TC-MVP-E2E-001 failed:\n- " + "\n- ".join(failures))
    print(
        "TC-MVP-E2E-001-SIM passed; REAL acceptance remains unsatisfied"
        if args.mode == "sim"
        else "TC-MVP-E2E-001-REAL preflight passed; no REAL effects were executed"
    )


if __name__ == "__main__":
    main()
