#!/usr/bin/env python3
"""Run the pinned TC-MVP-CI-001 oracle with deterministic effect traps."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/mvp-v2"
PIN_PATH = ROOT / "config/mvp-conformance-pin.json"

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
    real_commits_created: int = 0
    real_pushes: int = 0
    real_pull_requests_created: int = 0
    merge_actions: int = 0
    release_actions: int = 0
    deployment_actions: int = 0
    production_actions: int = 0
    secret_outputs: int = 0
    forward_count: int = 0


TRAPPED_EFFECTS = tuple(name for name in Effects.__dataclass_fields__ if name != "forward_count")


class FakeAdapters:
    """In-memory producer/router/target/receiver/source-consumer chain."""

    def __init__(self) -> None:
        self.effects = Effects()

    def producer(self, scenario: str) -> dict[str, str]:
        return {"scenario": scenario, "contract_version": "broken" if scenario == "unsupported-version" else "ai-sdlc-contract/v2"}

    def router(self, task: dict[str, str]) -> dict[str, str] | None:
        return None if task["scenario"] in REJECTED - {"receiver-rejection"} else task

    def target(self, execution: dict[str, str]) -> dict[str, str] | None:
        return None if execution["scenario"] == "missing-result" else execution

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
        # The released oracle has three effect counters. The expanded traps are
        # asserted separately so canonical expected results remain unchanged.
        observation = {
            "decision": decision,
            "codex_calls": self.effects.codex_calls,
            "real_branches_created": self.effects.real_branches_created,
            "real_pull_requests_created": self.effects.real_pull_requests_created,
            "forward_count": self.effects.forward_count,
        }
        if scenario == "disabled-target":
            observation["rejection_boundary"] = "router-activation"
        return observation


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def validate_pin(pin: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if pin.get("organization_repository") != "Young-Consultations/.github":
        errors.append("compatibility pin has the wrong organization repository")
    if pin.get("compatibility_sha") != "c6090e5bbadcc2102a1cb91875466e9decdada1e":
        errors.append("compatibility pin is not the approved immutable revision")
    compatibility_sha = str(pin.get("compatibility_sha", ""))
    files = pin.get("files")
    if not isinstance(files, dict):
        return errors + ["compatibility pin has no file identities"]
    try:
        tree = subprocess.run(
            ["git", "ls-tree", "-r", compatibility_sha, "--", *map(str, files)],
            # PIN_PATH remains anchored to this checkout when tests replace
            # ROOT to exercise local-file mismatch handling.
            cwd=PIN_PATH.parent.parent,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        compatibility_files = {
            line.split(maxsplit=3)[3]: line.split(maxsplit=3)[2]
            for line in tree.splitlines()
        }
    except (OSError, subprocess.CalledProcessError):
        return errors + ["approved compatibility revision is unavailable"]
    for relative, expected in files.items():
        relative = str(relative)
        compatibility_identity = compatibility_files.get(relative)
        if compatibility_identity is None:
            errors.append(f"pinned file is absent from compatibility revision: {relative}")
        elif expected != compatibility_identity:
            errors.append(f"pinned identity differs from compatibility revision: {relative}")
        path = ROOT / str(relative)
        if not path.is_file():
            errors.append(f"pinned file is missing: {relative}")
        elif git_blob_sha1(path.read_bytes()) != expected:
            errors.append(f"pinned file is incompatible: {relative}")
    return errors


def run(report_path: Path | None = None) -> list[str]:
    pin = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    cases = json.loads((FIXTURES / "scenarios.json").read_text(encoding="utf-8"))
    oracle = json.loads((FIXTURES / "expected-results.json").read_text(encoding="utf-8"))
    errors = validate_pin(pin)
    results = []
    if not (manifest["fixture_version"] == cases["fixture_version"] == oracle["fixture_version"] == pin["fixture_version"]):
        errors.append("fixture versions differ")
    ids = [case["id"] for case in cases["scenarios"]]
    if ids != manifest["scenarios"] or set(ids) != set(oracle["expected"]):
        errors.append("manifest, executable cases, and oracle differ")
    for case in cases["scenarios"]:
        before = len(errors)
        expected_case = {"id": case["id"], "adapter": "fake", "network": False, "codex": False,
                         "branch_effect": "none", "pull_request_effect": "none"}
        if case["id"] == "disabled-target":
            expected_case["rejection_boundary"] = "router-activation"
        fake = FakeAdapters()
        actual = fake.execute(case["id"])
        if case != expected_case:
            errors.append(f"{case['id']}: real-effect isolation violated")
        if actual != oracle["expected"][case["id"]]:
            errors.append(f"{case['id']}: expected {oracle['expected'][case['id']]!r}, got {actual!r}")
        nonzero = {name: getattr(fake.effects, name) for name in TRAPPED_EFFECTS if getattr(fake.effects, name)}
        if nonzero:
            errors.append(f"{case['id']}: prohibited effects observed: {nonzero}")
        results.append({"id": case["id"], "result": "pass" if len(errors) == before else "fail",
                        "decision": actual["decision"]})
    report = {
        "report_version": "1.0",
        "repository": "Young-Consultations/.github",
        "adapter_revision": pin["adapter_revision"],
        "compatibility_sha": pin["compatibility_sha"],
        "fixture_set": manifest["fixture_set"],
        "fixture_version": manifest["fixture_version"],
        "production_readiness_claim": False,
        "activation_requested": False,
        # This oracle exercises the shared in-memory chain, not this
        # repository's target adapter. Adapter tests are run separately in CI,
        # so this artifact must not represent itself as activation evidence.
        "activation_evidence_sufficient": False,
        "activation_evidence_reason": "shared fixtures were not executed through the repository adapter",
        "effect_traps": {name: 0 for name in TRAPPED_EFFECTS},
        "scenario_results": results,
        "failures": errors,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=ROOT / "reports/tc-mvp-ci-001.json")
    args = parser.parse_args()
    failures = run(args.report)
    if failures:
        raise SystemExit("TC-MVP-CI-001 failed:\n- " + "\n- ".join(failures))
    print("TC-MVP-CI-001: pinned oracle passed; all prohibited effect counters are zero")
