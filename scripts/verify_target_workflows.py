#!/usr/bin/env python3
"""Read-only verification of registered target workflow dispatch interfaces."""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/codex-repositories.json"
CANONICAL_VERSION = "ai-sdlc-contract/v2"
EXPECTED_INPUTS = {
    "execution_input_json": (False, "string"),
    "execution_input_artifact": (False, "string"),
    "execution_input_run_id": (False, "string"),
    "concurrency_group": (True, "string"),
}
CONTRACT_FIELDS = {
    "contract_version", "correlation_id", "source_issue", "target_repository",
    "task_type", "execution_mode", "project", "priority", "executor",
    "parallel_safe", "draft_pr_only", "instructions", "requested_branch",
    "timeout_minutes",
}
WORKFLOW_REF_RE = re.compile(
    r"^(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/"
    r"(?P<path>\.github/workflows/[^@]+\.ya?ml)@(?P<ref>[^@\s]+)$"
)


class CompatibilityError(ValueError):
    """An actionable registry or target compatibility failure."""


class GithubSafeLoader(yaml.SafeLoader):
    """Safe YAML loader which does not interpret GitHub's `on` key as boolean."""


# PyYAML implements YAML 1.1, where "on" is a boolean. GitHub uses YAML 1.2.
GithubSafeLoader.yaml_implicit_resolvers = {
    key: [item for item in values if item[0] != "tag:yaml.org,2002:bool"]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
GithubSafeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.IGNORECASE), list("tTfF")
)


def parse_workflow_ref(value: Any) -> tuple[str, str, str]:
    if not isinstance(value, str) or not (match := WORKFLOW_REF_RE.fullmatch(value)):
        raise CompatibilityError("malformed workflow_ref")
    path = match.group("path")
    if ".." in path.split("/"):
        raise CompatibilityError("malformed workflow_ref")
    return match.group("repository"), path, match.group("ref")


def load_registry(path: Path = REGISTRY) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompatibilityError(f"registry cannot be loaded: {exc}") from exc
    repositories = data.get("repositories") if isinstance(data, dict) else None
    if not isinstance(repositories, dict):
        raise CompatibilityError("registry must contain a repositories mapping")
    for repository, entry in repositories.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("enabled"), bool):
            raise CompatibilityError(f"invalid registry entry: {repository}")
        if entry["enabled"]:
            workflow_repository, _, _ = parse_workflow_ref(entry.get("workflow_ref"))
            if workflow_repository != repository:
                raise CompatibilityError(f"{repository}: workflow_ref repository mismatch")
            if entry.get("contract_version") != CANONICAL_VERSION:
                raise CompatibilityError(f"{repository}: contract-version mismatch")
    return repositories


def parse_workflow(source: str) -> dict[str, Any]:
    try:
        document = yaml.load(source, Loader=GithubSafeLoader)
    except yaml.YAMLError as exc:
        raise CompatibilityError(f"invalid workflow YAML: {exc}") from exc
    if not isinstance(document, dict):
        raise CompatibilityError("workflow must be a YAML mapping")
    return document


def verify_interface(source: str) -> str:
    workflow = parse_workflow(source)
    triggers = workflow.get("on")
    dispatch = triggers.get("workflow_dispatch") if isinstance(triggers, dict) else None
    if not isinstance(dispatch, dict):
        raise CompatibilityError("workflow_dispatch is missing")
    inputs = dispatch.get("inputs")
    if not isinstance(inputs, dict):
        raise CompatibilityError("workflow_dispatch.inputs is missing")
    for name in ("execution_input_json", "concurrency_group"):
        if name not in inputs:
            raise CompatibilityError(f"missing {name}")
    for name, (required, input_type) in EXPECTED_INPUTS.items():
        if name not in inputs:  # Artifact inputs are optional declarations.
            continue
        definition = inputs[name]
        if not isinstance(definition, dict):
            raise CompatibilityError(f"{name} definition must be a mapping")
        if definition.get("type") != input_type:
            raise CompatibilityError(f"{name} must have type {input_type}")
        actual_required = definition.get("required", False)
        if not isinstance(actual_required, bool) or actual_required is not required:
            raise CompatibilityError(f"{name}.required must be {str(required).lower()}")
    obsolete = sorted(
        name for name in CONTRACT_FIELDS
        if isinstance(inputs.get(name), dict) and inputs[name].get("required") is True
    )
    if obsolete:
        raise CompatibilityError("contract fields must not be required separately: " + ", ".join(obsolete))
    return "direct JSON" + (" + optional artifact" if all(x in inputs for x in EXPECTED_INPUTS) else "")


def fetch_workflow(repository: str, path: str, ref: str, token: str | None = None) -> str:
    quoted_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
    url = f"https://api.github.com/repos/{repository}/contents/{quoted_path}?ref={urllib.parse.quote(ref, safe='')}"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        raise CompatibilityError(f"workflow is unavailable at registered ref: {getattr(exc, 'reason', exc)}") from exc
    try:
        # GitHub's Contents API wraps Base64 content across multiple lines.
        encoded_content = "".join(payload["content"].split())
        return base64.b64decode(encoded_content, validate=True).decode("utf-8")
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise CompatibilityError("GitHub returned invalid workflow content") from exc


def verify_registry(repositories: dict[str, dict[str, Any]], token: str | None) -> list[dict[str, str]]:
    report = []
    for repository, entry in repositories.items():
        if not entry["enabled"]:
            continue
        workflow_repository, path, ref = parse_workflow_ref(entry["workflow_ref"])
        row = {"repository": repository, "workflow": path, "ref": ref,
               "contract_version": entry["contract_version"], "transport_interface": "unknown", "result": "pass"}
        try:
            row["transport_interface"] = verify_interface(fetch_workflow(workflow_repository, path, ref, token))
            if ref in {"main", "master"}:
                row["result"] = "pass (warning: movable ref)"
        except CompatibilityError as exc:
            row["result"] = f"fail: {exc}"
        report.append(row)
    return report


def write_outputs(report: list[dict[str, str]], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"targets": report}, indent=2) + "\n", encoding="utf-8")
    lines = ["## AI-SDLC target compatibility", "", "| Repository | Workflow | Ref | Contract version | Transport interface | Result |",
             "| --- | --- | --- | --- | --- | --- |"]
    for row in report:
        lines.append("| " + " | ".join(row[key].replace("|", "\\|") for key in
                     ("repository", "workflow", "ref", "contract_version", "transport_interface", "result")) + " |")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--report", type=Path, default=ROOT / "reports/target-workflow-compatibility.json")
    parser.add_argument("--fixtures-only", action="store_true", help="validate the canonical local target fixture without network access")
    args = parser.parse_args(argv)
    try:
        repositories = load_registry(args.registry)
        if args.fixtures_only:
            fixture = ROOT / "tests/fixtures/target_workflows/portfolio-tasks-codex-execute.yml"
            interface = verify_interface(fixture.read_text(encoding="utf-8"))
            report = [{"repository": "Young-Consultations/portfolio-tasks", "workflow": ".github/workflows/codex-execute.yml",
                       "ref": "fixture", "contract_version": CANONICAL_VERSION, "transport_interface": interface, "result": "pass"}]
        else:
            token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
            report = verify_registry(repositories, token)
        write_outputs(report, args.report)
        return int(any(row["result"].startswith("fail") for row in report))
    except (CompatibilityError, OSError) as exc:
        print(f"compatibility verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
