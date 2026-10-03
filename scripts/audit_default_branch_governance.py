#!/usr/bin/env python3
"""Audit GitHub rulesets for fail-closed default-branch change control."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config" / "default-branch-governance.json"
API_ROOT = "https://api.github.com"


def load_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema_version") != 1:
        raise ValueError("unsupported default-branch governance policy schema")
    repos = policy.get("repositories")
    required = policy.get("required_default_branch_ruleset")
    if not isinstance(repos, list) or not repos or not all(isinstance(x, str) and "/" in x for x in repos):
        raise ValueError("policy repositories must be a non-empty owner/repository list")
    if not isinstance(required, dict):
        raise ValueError("policy required_default_branch_ruleset must be an object")
    return policy


def evaluate_rulesets(rulesets: list[dict[str, Any]], policy: dict[str, Any]) -> list[str]:
    """Return compliance errors for one repository's expanded rulesets."""
    required = policy["required_default_branch_ruleset"]
    required_types = set(required["required_rule_types"])
    include_ref = required["include_ref"]

    candidates: list[dict[str, Any]] = []
    for ruleset in rulesets:
        if ruleset.get("target") != required["target"]:
            continue
        if ruleset.get("enforcement") != required["enforcement"]:
            continue
        ref_condition = ruleset.get("conditions", {}).get("ref_name", {})
        include = ref_condition.get("include", [])
        exclude = ref_condition.get("exclude", [])
        if include_ref not in include:
            continue
        if not isinstance(exclude, list) or exclude:
            continue
        candidates.append(ruleset)

    if not candidates:
        return ["no active branch ruleset targets ~DEFAULT_BRANCH"]

    candidate_errors: list[str] = []
    for ruleset in candidates:
        name = ruleset.get("name", "<unnamed>")
        rules = ruleset.get("rules", [])
        present_types = {rule.get("type") for rule in rules if isinstance(rule, dict)}
        missing = sorted(required_types - present_types)

        errors: list[str] = []
        if missing:
            errors.append(f"missing rule types: {', '.join(missing)}")

        if required.get("require_no_bypass_actors"):
            bypass_actors = ruleset.get("bypass_actors")
            if not isinstance(bypass_actors, list):
                errors.append("bypass actor state is unavailable or malformed")
            elif bypass_actors:
                errors.append("bypass actors are configured")

        pull_request_rule = next(
            (rule for rule in rules if isinstance(rule, dict) and rule.get("type") == "pull_request"),
            None,
        )
        if pull_request_rule is None:
            errors.append("pull_request rule is absent")
        else:
            pr_required = required.get("pull_request", {})
            pr_parameters = pull_request_rule.get("parameters", {})
            if pr_required.get("required_review_thread_resolution") is True and not pr_parameters.get(
                "required_review_thread_resolution"
            ):
                errors.append("pull_request rule does not require review-thread resolution")

        if not errors:
            return []

        candidate_errors.append(f"{name}: " + "; ".join(errors))

    return [
        "no single active default-branch ruleset satisfies the required fail-closed policy",
        *candidate_errors,
    ]


def _request_json(url: str, token: str | None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "young-consultations-default-branch-audit",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} for {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API request failed for {url}: {exc.reason}") from exc


def fetch_rulesets(repository: str, token: str | None) -> list[dict[str, Any]]:
    summaries = _request_json(f"{API_ROOT}/repos/{repository}/rulesets", token)
    if not isinstance(summaries, list):
        raise RuntimeError(f"unexpected ruleset list response for {repository}")

    expanded: list[dict[str, Any]] = []
    for summary in summaries:
        ruleset_id = summary.get("id")
        if not isinstance(ruleset_id, int):
            raise RuntimeError(f"ruleset without numeric id for {repository}")
        detail = _request_json(f"{API_ROOT}/repos/{repository}/rulesets/{ruleset_id}", token)
        if not isinstance(detail, dict):
            raise RuntimeError(f"unexpected ruleset detail response for {repository}/{ruleset_id}")
        expanded.append(detail)
    return expanded


def audit(policy: dict[str, Any], repositories: list[str], token: str | None) -> dict[str, Any]:
    results: dict[str, Any] = {}
    compliant = True

    for repository in repositories:
        try:
            rulesets = fetch_rulesets(repository, token)
            errors = evaluate_rulesets(rulesets, policy)
        except RuntimeError as exc:
            errors = [str(exc)]
            rulesets = []

        repo_compliant = not errors
        compliant = compliant and repo_compliant
        results[repository] = {
            "compliant": repo_compliant,
            "errors": errors,
            "ruleset_count": len(rulesets),
        }

    return {
        "schema_version": 1,
        "compliant": compliant,
        "repositories": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument(
        "--repository",
        action="append",
        dest="repositories",
        help="owner/repository to audit; repeatable. Defaults to policy scope.",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    try:
        policy = load_policy(args.policy)
        repositories = args.repositories or policy["repositories"]
        unknown = sorted(set(repositories) - set(policy["repositories"]))
        if unknown:
            raise ValueError("repositories outside policy scope: " + ", ".join(unknown))

        result = audit(policy, repositories, os.environ.get("GITHUB_TOKEN"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"default-branch governance audit configuration error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for repository, details in result["repositories"].items():
            status = "PASS" if details["compliant"] else "FAIL"
            print(f"{status} {repository}")
            for error in details["errors"]:
                print(f"  - {error}")

    return 0 if result["compliant"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
