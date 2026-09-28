#!/usr/bin/env python3
"""Check the deployed multi-repository composition without exposing secret values."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote

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


def named_values(
    repository: str,
    kind: str,
    audit_token: str,
    *,
    environment: str | None = None,
) -> set[str]:
    scope = (
        f"repos/{repository}/environments/{quote(environment, safe='')}"
        if environment is not None
        else f"repos/{repository}/actions"
    )
    rows = api(
        f"{scope}/{kind}?per_page=100", token=audit_token
    )
    field = "secrets" if kind == "secrets" else "variables"
    values = [item for row in rows if isinstance(row, dict) for item in row.get(field, [])]
    return {str(item.get("name")) for item in values if isinstance(item, dict)}


def organization_secret_selected_for_repository(
    repository: str,
    name: str,
    audit_token: str,
) -> bool:
    owner, separator, repository_name = repository.partition("/")
    if not separator or not owner or not repository_name:
        raise ValueError(f"invalid repository identity {repository!r}")
    encoded_name = quote(name, safe="")
    metadata = api_one(
        f"orgs/{owner}/actions/secrets/{encoded_name}",
        token=audit_token,
    )
    if (
        not isinstance(metadata, dict)
        or metadata.get("name") != name
        or not isinstance(metadata.get("visibility"), str)
    ):
        raise ValueError(
            f"organization secret {name} returned an invalid metadata response"
        )
    if metadata["visibility"] != "selected":
        return False
    rows = api(
        f"orgs/{owner}/actions/secrets/{encoded_name}/repositories?per_page=100",
        token=audit_token,
    )
    selected = {
        str(item.get("full_name")).casefold()
        for row in rows
        if isinstance(row, dict)
        for item in row.get("repositories", [])
        if isinstance(item, dict) and isinstance(item.get("full_name"), str)
    }
    return repository.casefold() in selected


def repository_variable_value(
    repository: str,
    name: str,
    audit_token: str,
) -> str:
    value = api_one(
        f"repos/{repository}/actions/variables/{quote(name, safe='')}",
        token=audit_token,
    )
    if (
        not isinstance(value, dict)
        or value.get("name") != name
        or not isinstance(value.get("value"), str)
    ):
        raise ValueError(f"repository variable {name} returned an invalid response")
    return value["value"]


def audit_result_sender_binding(audit_token: str) -> list[str]:
    policy = load("config/codex-result-trust.json")
    expected = {
        author.casefold()
        for author in policy.get("trusted_result_authors", [])
        if isinstance(author, str) and author.strip()
    }
    if not expected:
        return ["credentials: immutable trusted result-author policy is empty"]

    try:
        raw = repository_variable_value(
            "Young-Consultations/portfolio-tasks",
            "PORTFOLIO_RESULT_SENDERS",
            audit_token,
        )
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as exc:
        return [
            "credentials: cannot inspect Young-Consultations/portfolio-tasks "
            f"variable PORTFOLIO_RESULT_SENDERS: {exc}"
        ]

    actual = {
        value.strip().casefold()
        for value in raw.split(",")
        if value.strip()
    }
    if actual != expected:
        return [
            "credentials: Young-Consultations/portfolio-tasks variable "
            "PORTFOLIO_RESULT_SENDERS must exactly match immutable "
            "trusted_result_authors"
        ]
    return []


def audit_credentials(roles: dict[str, Any], audit_token: str) -> list[str]:
    failures: list[str] = []
    for repository, expected in roles.items():
        scopes: list[tuple[str | None, dict[str, Any]]] = [(None, expected)]
        scopes.extend(
            (environment, values)
            for environment, values in expected.get("environments", {}).items()
        )
        for environment, values in scopes:
            label = (
                repository
                if environment is None
                else f"{repository} environment {environment}"
            )
            try:
                actual_secrets = named_values(
                    repository,
                    "secrets",
                    audit_token,
                    environment=environment,
                )
                actual_variables = named_values(
                    repository,
                    "variables",
                    audit_token,
                    environment=environment,
                )
            except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
                failures.append(f"credentials: cannot inspect {label}: {exc}")
                continue
            for name in values.get("secrets", {}):
                if name in actual_secrets:
                    continue
                if environment is not None:
                    failures.append(f"credentials: {label} secret {name} is missing")
                    continue
                try:
                    selected_org_secret = organization_secret_selected_for_repository(
                        repository,
                        name,
                        audit_token,
                    )
                except (
                    subprocess.CalledProcessError,
                    json.JSONDecodeError,
                    ValueError,
                ) as exc:
                    failures.append(
                        f"credentials: cannot verify {label} secret {name} "
                        f"through organization scope: {exc}"
                    )
                    continue
                if not selected_org_secret:
                    failures.append(
                        f"credentials: {label} secret {name} is missing or is not "
                        "an organization secret restricted to this repository"
                    )
            for name in values.get("variables", {}):
                if name not in actual_variables:
                    failures.append(f"credentials: {label} variable {name} is missing")
    return failures


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
            failures.extend(audit_credentials(roles, audit_token))
            failures.extend(audit_result_sender_binding(audit_token))
        checks.append({
            "boundary": "credential-metadata",
            "status": "PASS" if not any(
                value.startswith("credentials:") for value in failures
            ) else "FAIL",
        })

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
