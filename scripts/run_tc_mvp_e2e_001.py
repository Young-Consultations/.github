#!/usr/bin/env python3
"""TC-MVP-E2E-001 dual-mode acceptance harness.

SIM executes the enabled target's immutable adapter and the control plane's
candidate receiver logic through deterministic fake external effects. REAL is a
fail-closed readiness check and never invokes Codex or mutates GitHub here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.codex_result_receiver import ADMISSION, JournalComment, ReceiverError, marker, receive

ACTIVATION = ROOT / "config/codex-activation.json"
REGISTRY = ROOT / "config/codex-repositories.json"
RELEASE_MANIFEST = ROOT / "release/release-manifest.json"
REAL_TARGET = "Young-Consultations/consulting-playbook"
PUBLISHED_BASELINE = "2.3.2"
CANDIDATE_RELEASE = "2.4.0"
TARGET_ROOT_ENV = "TC_MVP_E2E_TARGET_ROOT"


@dataclass
class EffectTraps:
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


TRAPPED_EFFECTS = tuple(EffectTraps.__dataclass_fields__)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_release_errors() -> list[str]:
    manifest = _load(RELEASE_MANIFEST)
    errors: list[str] = []
    if str(manifest.get("release_version")) != CANDIDATE_RELEASE:
        errors.append(f"expected release candidate {CANDIDATE_RELEASE}")
    if manifest.get("tag") != f"ai-sdlc-v{CANDIDATE_RELEASE}":
        errors.append("release candidate tag does not match candidate version")
    return errors


def _real_release_errors() -> list[str]:
    errors = _candidate_release_errors()
    manifest = _load(RELEASE_MANIFEST)
    if manifest.get("tag_published") is not True:
        errors.append(f"ai-sdlc-v{CANDIDATE_RELEASE} is not published; REAL remains blocked")
    return errors


def _activation_errors() -> list[str]:
    activation = _load(ACTIVATION).get("targets", {})
    enabled = sorted(name for name, value in activation.items() if value is True)
    return [] if enabled == [REAL_TARGET] else [f"expected sole enabled target {REAL_TARGET}, got {enabled}"]


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
    if not (target_root / ".git").exists():
        return ["target checkout is not a Git repository"]
    import subprocess

    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target_root, text=True).strip()
    return [] if actual == expected else [f"target checkout {actual} does not match registry adapter commit {expected}"]


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


def _payload() -> dict[str, Any]:
    payload = _load(ROOT / "contracts/examples/valid-execution-input.json")
    payload.update({
        "target_repository": REAL_TARGET,
        "task_type": "documentation",
        "execution_mode": "implement",
        "requested_branch": f"codex/{payload['delivery_id'].lower()}",
    })
    return payload


class FakeTargetEffects:
    """Target-owned adapter effect seam with no reachable real mutation APIs."""

    def __init__(self, adapter: ModuleType, traps: EffectTraps, *, found: list[dict[str, Any]] | None = None) -> None:
        self.adapter, self.traps, self.found = adapter, traps, found or []

    def discover(self, branch: str, delivery_id: str, timeout_seconds: float) -> Any:
        return self.adapter.Ownership(bool(self.found), self.found)

    def codex(self, instructions: str, timeout_seconds: float) -> None:
        if not instructions:
            raise ValueError("instructions must not be empty")

    def validate_candidate(self, timeout_seconds: float) -> tuple[bool, str]:
        return True, "passed"

    def publish(self, branch: str, delivery_id: str, digest: str, timeout_seconds: float) -> str:
        return "https://github.com/Young-Consultations/consulting-playbook/pull/999999"


class SimJournal:
    """In-memory external-effect seam around the real receiver implementation."""

    def __init__(self, payload: dict[str, Any]) -> None:
        binding = {key: payload[key] for key in (
            "contract_version", "delivery_id", "correlation_id", "source_issue", "target_repository"
        )}
        self.entries = [JournalComment(marker(ADMISSION, binding), "router-bot")]
        self.projections: list[dict[str, Any]] = []

    def authenticate(self, repository: str) -> None: return None
    def comments(self, repository: str, issue: int) -> list[JournalComment]: return list(self.entries)
    def trusted_author(self, author: str, role: str) -> bool:
        return author == ("router-bot" if role == "admission" else "receiver-bot")
    def append(self, repository: str, issue: int, body: str) -> None:
        self.entries.append(JournalComment(body, "receiver-bot"))
    def forward(self, repository: str, projection: dict[str, Any]) -> None:
        self.projections.append(projection)


def _managed(adapter: ModuleType, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": "https://github.com/Young-Consultations/consulting-playbook/pull/999999",
        "state": "OPEN", "draft": True, "digest": adapter.canonical_digest(payload),
    }


def _run_target(adapter: ModuleType, payload: dict[str, Any], effects: FakeTargetEffects) -> dict[str, Any]:
    return adapter.run_adapter(
        json.dumps(payload), payload["concurrency_group"], "router-app", {"router-app"}, effects
    ).result


def run_sim(report_path: Path, target_root: Path | None = None) -> list[str]:
    """Exercise the enabled target adapter and candidate receiver with fake effects."""
    target_root = target_root or _target_root()
    errors = _candidate_release_errors() + _activation_errors() + _target_identity_errors(target_root)
    traps, journal = EffectTraps(), None
    try:
        adapter = _load_target_adapter(target_root)
        if getattr(adapter, "TARGET", None) != REAL_TARGET:
            errors.append("loaded adapter does not identify the enabled target")
        payload, journal = _payload(), SimJournal(_payload())
        result = _run_target(adapter, payload, FakeTargetEffects(adapter, traps))
        if result.get("execution_status") != "draft-pr-created":
            errors.append(f"SIM expected draft-pr-created, got {result.get('execution_status')}")
        receipt = receive(json.dumps(result), payload["source_issue"], REAL_TARGET, journal)
        if not receipt.accepted or receipt.duplicate or len(journal.projections) != 1:
            errors.append("SIM receiver/source projection did not accept exactly once")

        replay = _run_target(adapter, payload, FakeTargetEffects(adapter, traps, found=[_managed(adapter, payload)]))
        if replay.get("execution_status") != "duplicate-reused":
            errors.append("SIM duplicate delivery did not reuse managed draft")
        replay_receipt = receive(json.dumps(replay), payload["source_issue"], REAL_TARGET, journal)
        if not replay_receipt.accepted or not replay_receipt.duplicate or len(journal.projections) != 1:
            errors.append("SIM equivalent duplicate result was not an idempotent no-op")

        conflicting = dict(result)
        conflicting["pull_request_url"] = "https://github.com/Young-Consultations/consulting-playbook/pull/999998"
        try:
            receive(json.dumps(conflicting), payload["source_issue"], REAL_TARGET, journal)
        except ReceiverError as exc:
            if not exc.ambiguous:
                errors.append("SIM conflicting duplicate was rejected without ambiguity")
        else:
            errors.append("SIM conflicting duplicate result did not fail closed")
    except (FileNotFoundError, ImportError, KeyError, TypeError, ValueError) as exc:
        result, replay = {}, {}
        errors.append(f"SIM harness error: {type(exc).__name__}: {exc}")

    effect_counts = {name: getattr(traps, name) for name in TRAPPED_EFFECTS}
    if any(effect_counts.values()):
        errors.append(f"SIM prohibited real effects observed: {effect_counts}")
    entry, manifest = _registry_entry(), _load(RELEASE_MANIFEST)
    report = {
        "test_id": "TC-MVP-E2E-001-SIM", "mode": "sim",
        "published_baseline": PUBLISHED_BASELINE,
        "candidate_release": CANDIDATE_RELEASE,
        "candidate_tag_published": manifest.get("tag_published") is True,
        "target": REAL_TARGET,
        "target_adapter_commit": entry["conformance"]["adapter_commit_sha"],
        "execution_provider": "fake", "shared_target_adapter_path": True,
        "shared_receiver_path": True, "sim_passed": not errors,
        "real_acceptance_satisfied": False,
        "primary_execution_status": result.get("execution_status"),
        "duplicate_execution_status": replay.get("execution_status"),
        "receiver_forward_count": len(journal.projections) if journal is not None else 0,
        "conflicting_duplicate_result": "ambiguous-rejected" if result else "not-run",
        "effect_traps": effect_counts, "failures": errors,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return errors


def run_real_preflight(sim_report_path: Path, target_root: Path | None = None) -> list[str]:
    """Fail closed until the corrected receiver is published and target-pinned."""
    target_root = target_root or _target_root()
    errors = (
        _real_release_errors() + _activation_errors() + _target_identity_errors(target_root)
        + _target_receiver_pin_errors(target_root)
    )
    if not sim_report_path.is_file():
        return errors + ["SIM evidence is missing"]
    sim = _load(sim_report_path)
    if sim.get("test_id") != "TC-MVP-E2E-001-SIM" or sim.get("sim_passed") is not True:
        errors.append("SIM evidence is not a passing TC-MVP-E2E-001-SIM report")
    if sim.get("real_acceptance_satisfied") is not False:
        errors.append("SIM evidence incorrectly claims REAL acceptance")
    if sim.get("shared_target_adapter_path") is not True or sim.get("shared_receiver_path") is not True:
        errors.append("SIM evidence did not exercise the shared target and receiver paths")
    entry = _registry_entry()
    if (
        sim.get("target") != REAL_TARGET
        or sim.get("candidate_release") != CANDIDATE_RELEASE
        or sim.get("target_adapter_commit") != entry["conformance"]["adapter_commit_sha"]
    ):
        errors.append("SIM evidence does not match current REAL target/candidate/adapter")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("sim", "real-preflight"), required=True)
    parser.add_argument("--target-root", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=ROOT / ".ai-sdlc/acceptance/tc-mvp-e2e-001-sim.json")
    parser.add_argument("--sim-report", type=Path, default=ROOT / ".ai-sdlc/acceptance/tc-mvp-e2e-001-sim.json")
    args = parser.parse_args()
    target_root = args.target_root.resolve() if args.target_root else None
    failures = run_sim(args.report, target_root) if args.mode == "sim" else run_real_preflight(args.sim_report, target_root)
    if failures:
        raise SystemExit("TC-MVP-E2E-001 failed:\n- " + "\n- ".join(failures))
    print(
        "TC-MVP-E2E-001-SIM passed; REAL acceptance remains unsatisfied"
        if args.mode == "sim"
        else "TC-MVP-E2E-001-REAL preflight passed; no REAL effects were executed"
    )


if __name__ == "__main__":
    main()
