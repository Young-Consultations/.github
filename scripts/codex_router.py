#!/usr/bin/env python3
"""Validate and dispatch organization Codex tasks without exposing secrets."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REGISTRY = Path("config/codex-repositories.json")
VALID_DEPENDENCY_STATES = {"satisfied", "none", "waived"}
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_RE = re.compile(r"[^a-z0-9._/-]+")


def out(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")
    else:
        print(f"{name}={value}")


def fail(message: str, result: str = "failure", code: int = 1) -> None:
    summary = sanitize(message)
    out("execution_result", result)
    out("validation_result", "failed")
    out("diagnostic_summary", summary)
    print(f"::error::{summary}")
    raise SystemExit(code)


def sanitize(value: str) -> str:
    value = re.sub(r"gh[pousr]_[A-Za-z0-9_]+", "[redacted-token]", value)
    value = re.sub(r"(?i)(token|secret|password)=\S+", r"\1=[redacted]", value)
    return value[:700]


def load_registry() -> dict[str, Any]:
    with REGISTRY.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    repos = data.get("repositories")
    if not isinstance(repos, dict):
        fail("Registry is missing a repositories mapping.")
    return repos


def normalize_component(value: str) -> str:
    lowered = value.strip().lower().replace(" ", "-")
    return SAFE_RE.sub("-", lowered).strip("-") or "unspecified"


def parse_metadata(raw: str) -> dict[str, Any]:
    try:
        metadata = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"approved_execution_metadata must be valid JSON: {exc.msg}")
    if not isinstance(metadata, dict):
        fail("approved_execution_metadata must be a JSON object.")
    if metadata.get("approved") is not True:
        fail("Task is missing approved execution metadata.")
    approved_by = str(metadata.get("approved_by", "")).strip()
    approval_id = str(metadata.get("approval_id", "")).strip()
    if not approved_by or not approval_id:
        fail("Approved metadata must include approved_by and approval_id.")
    return metadata


def validate() -> dict[str, str]:
    repos = load_registry()
    target = os.environ["TARGET_REPOSITORY"].strip()
    task_type = os.environ["TASK_TYPE"].strip().lower()
    component = os.environ["PROJECT_COMPONENT"].strip()
    dependency_status = os.environ["DEPENDENCY_STATUS"].strip().lower()
    parallel_safe = os.environ.get("PARALLEL_SAFE", "false").lower() == "true"

    if not REPO_RE.match(target):
        fail("target_repository must use owner/name format.")
    if target not in repos:
        fail(f"Repository {target} is not registered for Codex routing.")
    entry = repos[target]
    if not entry.get("enabled", False):
        fail(f"Repository {target} is disabled for Codex routing.")
    if task_type not in [str(item).lower() for item in entry.get("allowed_task_types", [])]:
        fail(f"Task type {task_type} is not allowed for {target}.")
    if dependency_status not in VALID_DEPENDENCY_STATES:
        fail("dependency_status must be satisfied, none, or waived.")
    parse_metadata(os.environ["APPROVED_EXECUTION_METADATA"])

    max_parallel = int(entry.get("max_parallel_tasks", 1))
    if max_parallel < 1:
        fail(f"Repository {target} has invalid max_parallel_tasks.")
    normalized_component = normalize_component(component)
    repo_key = target.lower().replace("/", "-")
    group = f"codex-{repo_key}-{os.getpid() if parallel_safe else normalized_component}"

    workflow_ref = str(entry.get("execution_workflow", {}).get("workflow_ref", ""))
    if not workflow_ref:
        fail(f"Repository {target} is missing an execution workflow reference.")

    outputs = {
        "execution_result": "validated",
        "validation_result": "passed",
        "target_repository": target,
        "codex_environment": str(entry.get("codex_environment", "placeholder-required")),
        "workflow_ref": workflow_ref,
        "concurrency_group": group,
        "diagnostic_summary": "Routing validation passed; target workflow dispatch is ready.",
    }
    for key, value in outputs.items():
        out(key, value)
    return outputs


def dispatch() -> None:
    workflow_ref = os.environ["WORKFLOW_REF"]
    target = os.environ["TARGET_REPOSITORY"]
    workflow_path = workflow_ref.split("/.github/workflows/", 1)[-1].split("@", 1)[0]
    ref = workflow_ref.rsplit("@", 1)[-1] if "@" in workflow_ref else "main"

    payload = {
        "source_issue": os.environ["SOURCE_ISSUE"],
        "task_type": os.environ["TASK_TYPE"],
        "project_component": os.environ["PROJECT_COMPONENT"],
        "priority": os.environ["PRIORITY"],
        "parallel_safe": os.environ["PARALLEL_SAFE"],
        "dependency_status": os.environ["DEPENDENCY_STATUS"],
        "codex_environment": os.environ["CODEX_ENVIRONMENT"],
        "concurrency_group": os.environ["CONCURRENCY_GROUP"],
        "draft_pr_only": "true",
    }
    cmd = ["gh", "workflow", "run", workflow_path, "--repo", target, "--ref", ref]
    for key, value in payload.items():
        cmd.extend(["-f", f"{key}={value}"])

    try:
        subprocess.run(cmd, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        fail(f"Target workflow dispatch failed for {target}: {sanitize(exc.stderr or exc.stdout)}", result="dispatch_failed")

    branch = f"codex/{normalize_component(os.environ['PROJECT_COMPONENT'])}/{int(time.time())}"
    out("execution_result", "dispatched")
    out("generated_branch", branch)
    out("draft_pr_url", "pending-target-workflow")
    out("test_result", "pending-target-workflow")
    out("diagnostic_summary", "Target workflow dispatched. Branch, draft PR URL, and tests are finalized by the target repository workflow.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"validate", "dispatch"}:
        print("Usage: codex_router.py validate|dispatch", file=sys.stderr)
        raise SystemExit(2)
    if sys.argv[1] == "validate":
        validate()
    else:
        dispatch()
