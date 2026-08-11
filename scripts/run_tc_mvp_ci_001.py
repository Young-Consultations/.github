#!/usr/bin/env python3
"""Execute the organization-owned deterministic TC-MVP-CI-001 oracle."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/mvp-v2"


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
        if case != {"id": case["id"], "adapter": "fake", "network": False, "codex": False, "branch_effect": "none", "pull_request_effect": "none"}:
            errors.append(f"{case['id']}: real-effect isolation violated")
        result = oracle["expected"][case["id"]]
        for counter in manifest["required_zero_effect_counters"]:
            if result[counter] != 0:
                errors.append(f"{case['id']}: {counter} was nonzero")
    return errors


if __name__ == "__main__":
    failures = run()
    if failures:
        raise SystemExit("TC-MVP-CI-001 failed:\n- " + "\n- ".join(failures))
    print("TC-MVP-CI-001: all fake-adapter scenarios passed with zero real effects")
