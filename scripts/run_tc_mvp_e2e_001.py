#!/usr/bin/env python3
"""TC-MVP-E2E-001 shared acceptance harness.

SIM reuses the real target adapter with deterministic effect seams. REAL performs
strict readiness preflight only; the human-gated workflow remains responsible
for invoking the deployed integration after review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.run_tc_mvp_ci_001 import (
    Effects,
    TrappedReceiver,
    TrappedTargetEffects,
    TRAPPED_EFFECTS,
    _adapter,
    _managed,
    _payload,
)

ROOT = Path(__file__).resolve().parents[1]
ACTIVATION = ROOT / "config/codex-activation.json"
RELEASE_MANIFEST = ROOT / "release/release-manifest.json"
REAL_TARGET = "Young-Consultations/consulting-playbook"
RELEASE = "2.3.2"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _activation_errors() -> list[str]:
    activation = _load(ACTIVATION).get("targets", {})
    enabled = sorted(name for name, value in activation.items() if value is True)
    if enabled != [REAL_TARGET]:
        return [f"expected sole enabled target {REAL_TARGET}, got {enabled}"]
    return []


def _release_errors() -> list[str]:
    manifest = _load(RELEASE_MANIFEST)
    errors: list[str] = []
    if str(manifest.get("release_version")) != RELEASE:
        errors.append(f"expected release_version {RELEASE}")
    if manifest.get("status") != "published":
        errors.append("release manifest is not published")
    return errors


def run_sim(report_path: Path) -> list[str]:
    """Exercise the shared target/result path with deterministic fake effects."""
    errors = _release_errors() + _activation_errors()
    traps = Effects()
    receiver = TrappedReceiver()
    payload = _payload()
    payload["target_repository"] = REAL_TARGET
    payload["execution_mode"] = "implement"

    registry = _load(ROOT / "config/codex-repositories.json")
    effects = TrappedTargetEffects(traps)
    result = _adapter(payload, registry, effects)
    if result.get("execution_status") != "draft-pr-created":
        errors.append(f"SIM expected draft-pr-created, got {result.get('execution_status')}")
    if receiver.receive(result) != "accepted" or receiver.forward_count != 1:
        errors.append("SIM receiver/source projection did not accept exactly once")

    replay = _adapter(
        payload,
        registry,
        TrappedTargetEffects(traps, found=[_managed(payload)]),
    )
    if replay.get("execution_status") != "duplicate-reused":
        errors.append("SIM duplicate delivery did not reuse managed draft")

    conflicting = dict(result)
    conflicting["completed_at"] = "2099-01-01T00:00:00Z"
    if receiver.receive(conflicting) != "ambiguous-rejected":
        errors.append("SIM conflicting duplicate result did not fail closed")

    effect_counts = {name: getattr(traps, name) for name in TRAPPED_EFFECTS}
    if any(effect_counts.values()):
        errors.append(f"SIM prohibited real effects observed: {effect_counts}")

    report = {
        "test_id": "TC-MVP-E2E-001-SIM",
        "mode": "sim",
        "release": RELEASE,
        "target": REAL_TARGET,
        "execution_provider": "fake",
        "shared_adapter_path": True,
        "sim_passed": not errors,
        "real_acceptance_satisfied": False,
        "primary_execution_status": result.get("execution_status"),
        "duplicate_execution_status": replay.get("execution_status"),
        "receiver_forward_count": receiver.forward_count,
        "conflicting_duplicate_result": "ambiguous-rejected",
        "effect_traps": effect_counts,
        "failures": errors,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return errors


def run_real_preflight(sim_report_path: Path) -> list[str]:
    """Fail closed unless REAL prerequisites are satisfied.

    This function intentionally performs no Codex, branch, PR, receiver, or
    source mutation. The reviewed workflow uses this result as the gate before
    a separately authorized REAL invocation.
    """
    errors = _release_errors() + _activation_errors()
    if not sim_report_path.is_file():
        errors.append("SIM evidence is missing")
        return errors
    sim = _load(sim_report_path)
    if sim.get("test_id") != "TC-MVP-E2E-001-SIM" or sim.get("sim_passed") is not True:
        errors.append("SIM evidence is not a passing TC-MVP-E2E-001-SIM report")
    if sim.get("real_acceptance_satisfied") is not False:
        errors.append("SIM evidence incorrectly claims REAL acceptance")
    if sim.get("target") != REAL_TARGET or sim.get("release") != RELEASE:
        errors.append("SIM evidence does not match current REAL target/release")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("sim", "real-preflight"), required=True)
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

    failures = run_sim(args.report) if args.mode == "sim" else run_real_preflight(args.sim_report)
    if failures:
        raise SystemExit("TC-MVP-E2E-001 failed:\n- " + "\n- ".join(failures))
    if args.mode == "sim":
        print("TC-MVP-E2E-001-SIM passed; REAL acceptance remains unsatisfied")
    else:
        print("TC-MVP-E2E-001-REAL preflight passed; no REAL effects were executed")


if __name__ == "__main__":
    main()
