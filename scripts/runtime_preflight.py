#!/usr/bin/env python3
"""Check the deployed multi-repository composition without exposing secret values."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def api(endpoint: str, *, token: str | None = None) -> Any:
    env = None if token is None else {**os.environ, "GH_TOKEN": token}
    completed = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", endpoint],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    pages = json.loads(completed.stdout)
    return [item for page in pages for item in page] if all(isinstance(page, list) for page in pages) else pages


def api_one(endpoint: str, *, token: str | None = None) -> Any:
    env = None if token is None else {**os.environ, "GH_TOKEN": token}
    completed = subprocess.run(
        ["gh", "api", endpoint], check=True, text=True, capture_output=True, env=env,
    )
    return json.loads(completed.stdout)


def remote_tag_commit(tag: str) -> str:
    value = api_one(f"repos/Young-Consultations/.github/git/ref/tags/{tag}")
    obj = value.get("object") if isinstance(value, dict) else None
    for _ in range(4):
        if not isinstance(obj, dict):
            break
        if obj.get("type") == "commit" and isinstance(obj.get("sha"), str):
            return obj["sha"]
        if obj.get("type") != "tag" or not isinstance(obj.get("sha"), str):
            break
        tag_object = api_one(
            f"repos/Young-Consultations/.github/git/tags/{obj['sha']}"
        )
        obj = tag_object.get("object") if isinstance(tag_object, dict) else None
    raise ValueError("release tag does not resolve to a commit")


def named_values(repository: str, kind: str, audit_token: str) -> set[str]:
    rows = api(
        f"repos/{repository}/actions/{kind}?per_page=100", token=audit_token
    )
    field = "secrets" if kind == "secrets" else "variables"
    values = [item for row in rows if isinstance(row, dict) for item in row.get(field, [])]
    return {str(item.get("name")) for item in values if isinstance(item, dict)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--candidate", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    runtime = load("release/current-runtime.json")
    roles = load("config/codex-credential-roles.json")["repositories"]
    failures: list[str] = []
    checks: list[dict[str, str]] = []

    enabled = runtime["activation"]["enabled_targets"]
    if enabled != ["Young-Consultations/consulting-playbook"]:
        failures.append(f"activation: expected only consulting-playbook, got {enabled}")
    checks.append({"boundary": "activation", "status": "PASS" if not failures else "FAIL"})
    if runtime["release_state"] != "published" and not args.candidate:
        failures.append(
            f"release: {runtime['control_plane']['tag']} is not yet published"
        )
    checks.append({
        "boundary": "release-publication",
        "status": "PASS" if runtime["release_state"] == "published" else (
            "CANDIDATE" if args.candidate else "FAIL"
        ),
    })

    if runtime["release_state"] == "published" and not args.offline:
        expected_commit = runtime["control_plane"].get("tag_commit_sha")
        try:
            actual_commit = remote_tag_commit(runtime["control_plane"]["tag"])
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"release-tag: cannot resolve remote tag: {exc}")
        else:
            if actual_commit != expected_commit:
                failures.append(
                    "release-tag: remote tag does not match the reviewed commit"
                )
        checks.append({
            "boundary": "remote-release-tag",
            "status": "PASS" if not any(
                value.startswith("release-tag:") for value in failures
            ) else "FAIL",
        })

    if not args.offline:
        audit_token = os.environ.get("PREFLIGHT_AUDIT_TOKEN")
        if not audit_token:
            failures.append("credentials: PREFLIGHT_AUDIT_TOKEN is unavailable")
        else:
            for repository, expected in roles.items():
                try:
                    actual_secrets = named_values(repository, "secrets", audit_token)
                    actual_variables = named_values(repository, "variables", audit_token)
                except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
                    failures.append(f"credentials: cannot inspect {repository}: {exc}")
                    continue
                for name in expected["secrets"]:
                    if name not in actual_secrets:
                        failures.append(f"credentials: {repository} secret {name} is missing")
                for name in expected["variables"]:
                    if name not in actual_variables:
                        failures.append(f"credentials: {repository} variable {name} is missing")
            checks.append({"boundary": "credential-metadata", "status": "PASS" if not any(value.startswith("credentials:") for value in failures) else "FAIL"})

    result = {
        "status": "PASS" if not failures else "FAIL",
        "release": runtime["control_plane"]["tag"],
        "release_state": runtime["release_state"],
        "checks": checks,
        "failures": failures,
        "next_action": "run SIM" if not failures else failures[0],
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
