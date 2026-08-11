#!/usr/bin/env python3
"""Execute TC-MVP-CI-001 through deterministic, no-effect fake adapters."""
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/mvp-v2"

REJECTED = {
    "unsupported-version", "malformed-payload", "unauthorized-approval",
    "stale-approval", "withdrawn-approval", "queued-task-at-admission",
    "material-change-old-task-id", "unknown-target", "disabled-target",
    "receiver-rejection",
}
AMBIGUOUS = {
    "conflicting-duplicate-result", "ambiguous-result", "ownership-conflict",
    "create-race-ambiguous",
}
NO_FORWARD = REJECTED | AMBIGUOUS | {
    "duplicate-delivery", "identical-duplicate-result", "missing-result",
    "no-real-effects",
}


@dataclass
class Effects:
    codex_calls: int = 0
    real_branches_created: int = 0
    real_pull_requests_created: int = 0
    forward_count: int = 0


class FakeAdapters:
    """In-memory producer/router/target/receiver/source-consumer chain."""

    def __init__(self) -> None:
        self.effects = Effects()

    def producer(self, scenario: str) -> dict[str, str]:
        return {"scenario": scenario, "contract_version": "broken" if scenario == "unsupported-version" else "ai-sdlc-contract/v2"}

    def router(self, task: dict[str, str]) -> dict[str, str] | None:
        return None if task["scenario"] in REJECTED - {"receiver-rejection"} else task

    def target(self, execution: dict[str, str]) -> dict[str, str] | None:
        if execution["scenario"] == "missing-result":
            return None
        return execution

    def receiver(self, result: dict[str, str]) -> tuple[str, dict[str, str] | None]:
        scenario = result["scenario"]
        if scenario in AMBIGUOUS:
            return "ambiguous-rejected", None
        if scenario == "receiver-rejection":
            return "rejected", None
        if scenario in NO_FORWARD:
            return "accepted", None
        return "accepted", result

    def source_consumer(self, projection: dict[str, str]) -> None:
        self.effects.forward_count += 1

    def execute(self, scenario: str) -> dict[str, int | str]:
        task = self.producer(scenario)
        execution = self.router(task)
        if execution is None:
            decision = "rejected"
        else:
            result = self.target(execution)
            if result is None:
                decision = "pending-timeout"
            else:
                decision, projection = self.receiver(result)
                if projection is not None:
                    self.source_consumer(projection)
        observation = {"decision": decision, **vars(self.effects)}
        if scenario == "disabled-target":
            observation["rejection_boundary"] = "router-activation"
        return observation


def run() -> list[str]:
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    cases = json.loads((FIXTURES / "scenarios.json").read_text())
    oracle = json.loads((FIXTURES / "expected-results.json").read_text())
    errors = []
    if not (manifest["fixture_version"] == cases["fixture_version"] == oracle["fixture_version"]):
        errors.append("fixture versions differ")
    ids = [case["id"] for case in cases["scenarios"]]
    if ids != manifest["scenarios"] or set(ids) != set(oracle["expected"]):
        errors.append("manifest, executable cases, and oracle differ")
    for case in cases["scenarios"]:
        expected_case = {"id": case["id"], "adapter": "fake", "network": False, "codex": False,
                         "branch_effect": "none", "pull_request_effect": "none"}
        if case["id"] == "disabled-target":
            expected_case["rejection_boundary"] = "router-activation"
        if case != expected_case:
            errors.append(f"{case['id']}: real-effect isolation violated")
            continue
        actual = FakeAdapters().execute(case["id"])
        expected = oracle["expected"][case["id"]]
        if actual != expected:
            errors.append(f"{case['id']}: expected {expected!r}, got {actual!r}")
    return errors


if __name__ == "__main__":
    failures = run()
    if failures:
        raise SystemExit("TC-MVP-CI-001 failed:\n- " + "\n- ".join(failures))
    print("TC-MVP-CI-001: all fake-adapter scenarios passed with zero real effects")
