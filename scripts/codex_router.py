#!/usr/bin/env python3
"""Validate a canonical task and dispatch one canonical execution contract."""
from __future__ import annotations

import json
import os
import re
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/codex-repositories.json"
TASK_SCHEMA = ROOT / "contracts/task-contract.schema.json"
INPUT_SCHEMA = ROOT / "contracts/execution-input.schema.json"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_RE = re.compile(r"[^a-z0-9._-]+")
# workflow_dispatch accepts only a branch or tag for --ref. Adapter release tags
# use this governed, non-moving namespace so dispatchability and immutability
# are enforced together.
IMMUTABLE_ADAPTER_TAG_RE = re.compile(
    r"codex-adapter-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
)
FAILURE_CATEGORIES = {
    "contract-validation", "authorization", "dependency",
    "repository-routing", "publication", "unknown",
}
REGISTRY_FIELDS = {
    "enabled", "workflow_ref", "allowed_task_types", "codex_environment",
    "max_parallel_tasks", "draft_pr_only", "contract_version", "idempotency",
}


def parse_workflow_ref(repository: str, workflow_ref: Any) -> tuple[str, str]:
    """Return the workflow path and git ref from a registry workflow reference."""
    prefix = f"{repository}/.github/workflows/"
    if not isinstance(workflow_ref, str) or not workflow_ref.startswith(prefix):
        reject("repository-routing", f"Registry entry {repository} has an invalid workflow_ref.")
    remainder = workflow_ref[len(prefix):]
    if remainder.count("@") != 1:
        reject("repository-routing", f"Registry entry {repository} has an invalid workflow_ref.")
    workflow_path, ref = remainder.split("@", 1)
    if (
        not workflow_path
        or workflow_path.startswith("/")
        or ".." in workflow_path.split("/")
        or not workflow_path.endswith((".yml", ".yaml"))
        or workflow_path in {"codex-router.yml", "router-smoke-test.yml", "issue-to-codex.yml"}
        or not ref.strip()
    ):
        reject("repository-routing", f"Registry entry {repository} has an invalid workflow_ref.")
    return workflow_path, ref


def output(name: str, value: Any) -> None:
    rendered = value if isinstance(value, str) else json.dumps(value, separators=(",", ":"), sort_keys=True)
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={rendered}\n")
    else:
        print(f"{name}={rendered}")


def sanitize(value: str) -> str:
    value = re.sub(r"gh[pousr]_[A-Za-z0-9_]+", "[redacted-token]", value)
    value = re.sub(r"(?i)(token|secret|password)=\S+", r"\1=[redacted]", value)
    return value.replace("\n", " ")[:700]


def reject(category: str, message: str, correlation_id: str = "unknown") -> NoReturn:
    if category not in FAILURE_CATEGORIES:
        category = "unknown"
    result = {
        "correlation_id": correlation_id,
        "delivery_id": correlation_id,
        "execution_status": "rejected",
        "failure_category": category,
        "failure_message": sanitize(message),
    }
    output("execution_result", result)
    output("validation_result", "failed")
    output("failure_category", category)
    output("diagnostic_summary", result["failure_message"])
    print(f"::error::{result['failure_message']}")
    raise SystemExit(1)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_registry() -> dict[str, Any]:
    try:
        data = read_json(REGISTRY)
    except (OSError, json.JSONDecodeError) as exc:
        reject("repository-routing", f"Registry cannot be loaded: {exc}")
    repositories = data.get("repositories")
    if data.get("registry_format_version") != 1:
        reject("repository-routing", "Registry must declare supported registry_format_version 1.")
    if not isinstance(repositories, dict) or not repositories:
        reject("repository-routing", "Registry must contain a non-empty repositories mapping.")
    supported_types = set(read_json(TASK_SCHEMA)["$defs"]["taskType"]["enum"])
    for name, entry in repositories.items():
        if not REPO_RE.fullmatch(name) or not isinstance(entry, dict):
            reject("repository-routing", f"Invalid repository registry entry: {name}")
        missing = REGISTRY_FIELDS - entry.keys()
        if missing:
            reject("repository-routing", f"Registry entry {name} is missing: {', '.join(sorted(missing))}")
        if not isinstance(entry["enabled"], bool) or not isinstance(entry["draft_pr_only"], bool):
            reject("repository-routing", f"Registry entry {name} has invalid boolean policy.")
        if entry["draft_pr_only"] is not True:
            reject("repository-routing", f"Registry entry {name} must enforce draft_pr_only.")
        if not isinstance(entry["max_parallel_tasks"], int) or entry["max_parallel_tasks"] < 1:
            reject("repository-routing", f"Registry entry {name} has invalid max_parallel_tasks.")
        if not isinstance(entry["allowed_task_types"], list) or not entry["allowed_task_types"] or not set(entry["allowed_task_types"]) <= supported_types:
            reject("repository-routing", f"Registry entry {name} has invalid allowed_task_types.")
        _, workflow_revision = parse_workflow_ref(name, entry["workflow_ref"])
        if entry["enabled"] and not IMMUTABLE_ADAPTER_TAG_RE.fullmatch(workflow_revision):
            reject(
                "repository-routing",
                f"Enabled registry entry {name} must use a governed immutable "
                "codex-adapter-v* release tag.",
            )
        if not isinstance(entry["codex_environment"], str) or not entry["codex_environment"]:
            reject("repository-routing", f"Registry entry {name} has an invalid codex_environment.")
        idempotency = entry.get("idempotency")
        if not isinstance(idempotency, dict) or idempotency.get("branch_identity") != "delivery_id" or idempotency.get("ownership_marker") != "ai-sdlc-delivery-id" or idempotency.get("requires_preflight") is not True or idempotency.get("requires_fail_closed_reuse") is not True or idempotency.get("requires_create_race_requery") is not True or idempotency.get("terminal_reuse_status") != "duplicate-reused":
            reject("repository-routing", f"Registry entry {name} lacks required target idempotency policy.")
        if entry["contract_version"] != read_json(INPUT_SCHEMA)["properties"]["contract_version"]["const"]:
            reject("repository-routing", f"Registry entry {name} has an unsupported contract_version.")
    return repositories


def slug(value: str) -> str:
    return SAFE_RE.sub("-", value.strip().lower().replace("/", "-")).strip("-") or "unspecified"


def load_task() -> dict[str, Any]:
    raw = os.environ.get("TASK_PAYLOAD", "")
    try:
        task = json.loads(raw)
    except json.JSONDecodeError as exc:
        reject("contract-validation", f"task_payload must be valid JSON: {exc.msg}")
    if not isinstance(task, dict):
        reject("contract-validation", "task_payload must be a JSON object.")
    correlation_id = str(task.get("task_id", "unknown"))
    errors = sorted(Draft202012Validator(read_json(TASK_SCHEMA)).iter_errors(task), key=lambda e: list(e.path))
    if errors:
        reject("contract-validation", f"Task contract validation failed: {errors[0].message}", correlation_id)
    return task


def validate() -> dict[str, Any]:
    repositories = validate_registry()
    task = load_task()
    correlation_id = task["task_id"]
    delivery_id = task["task_id"]
    execution_mode = os.environ.get("EXECUTION_MODE", "implement")
    if execution_mode not in {"verify", "implement"}:
        reject("contract-validation", "Execution mode must be verify or implement.", correlation_id)
    # v2 carries no separate approval record. Consequently the trust boundary
    # accepts only its explicit approved state; queued is a later projection.
    if task["status"] != "approved":
        reject("authorization", "Task status is not approved for execution.", correlation_id)
    if task["executor"] != "codex":
        reject("authorization", "Task executor must be codex.", correlation_id)
    if task["dependencies"]:
        reject("dependency", "Task has unresolved dependencies.", correlation_id)

    target = task["target_repository"]
    entry = repositories.get(target)
    if entry is None:
        reject("repository-routing", f"Repository {target} is not registered.", correlation_id)
    if not entry["enabled"]:
        reject("repository-routing", f"Repository {target} is disabled.", correlation_id)
    if task["task_type"] not in entry["allowed_task_types"]:
        reject("repository-routing", f"Task type {task['task_type']} is not allowed for {target}.", correlation_id)
    if task["contract_version"] != entry["contract_version"]:
        reject("contract-validation", "Task contract version is not supported by the target.", correlation_id)

    issue = slug(task["source_issue"])
    boundary = slug(correlation_id if task["parallel_safe"] else task["project"])
    mode = "parallel" if task["parallel_safe"] else "serial"
    group = f"codex-{slug(target)}-{issue}-{mode}-{boundary}"
    execution = {
        "contract_version": entry["contract_version"],
        "correlation_id": correlation_id,
        "delivery_id": delivery_id,
        "source_issue": task["source_issue"],
        "target_repository": target,
        "task_type": task["task_type"],
        "execution_mode": execution_mode,
        "project": task["project"],
        "priority": task["priority"],
        "executor": task["executor"],
        "parallel_safe": task["parallel_safe"],
        "draft_pr_only": entry["draft_pr_only"],
        "instructions": task["instructions"],
        "requested_branch": f"codex/{slug(delivery_id)}",
        "concurrency_group": group,
        "timeout_minutes": 60,
    }
    errors = list(Draft202012Validator(read_json(INPUT_SCHEMA)).iter_errors(execution))
    if errors:
        reject("contract-validation", f"Execution input validation failed: {errors[0].message}", correlation_id)

    values = {
        "execution_result": "validated", "validation_result": "passed",
        "target_repository": target, "workflow_ref": entry["workflow_ref"],
        "codex_environment": entry["codex_environment"], "concurrency_group": group,
        "execution_input": execution, "correlation_id": correlation_id, "delivery_id": delivery_id,
        "diagnostic_summary": "Canonical task accepted and execution input validated.",
    }
    for key, value in values.items():
        output(key, value)
    return values


def dispatch() -> None:
    try:
        execution = json.loads(os.environ["EXECUTION_INPUT"])
    except (KeyError, json.JSONDecodeError) as exc:
        reject("contract-validation", f"Validated execution input is unavailable: {exc}")
    correlation_id = str(execution.get("correlation_id", "unknown"))
    delivery_id = str(execution.get("delivery_id", correlation_id))
    errors = list(Draft202012Validator(read_json(INPUT_SCHEMA)).iter_errors(execution))
    if errors:
        reject("contract-validation", f"Execution input validation failed: {errors[0].message}", correlation_id)
    concurrency_group = execution.get("concurrency_group")
    if not isinstance(concurrency_group, str) or not concurrency_group.strip():
        reject("contract-validation", "Execution input requires a non-empty concurrency_group.", correlation_id)

    repositories = validate_registry()
    target_repository = execution["target_repository"]
    entry = repositories.get(target_repository)
    if entry is None:
        reject("repository-routing", f"Repository {target_repository} is not registered.", correlation_id)
    workflow_ref = os.environ.get("WORKFLOW_REF", "")
    if workflow_ref != entry["workflow_ref"]:
        reject("repository-routing", "Workflow reference does not match the target registry entry.", correlation_id)
    workflow_path, ref = parse_workflow_ref(target_repository, workflow_ref)
    immutable = {key: execution[key] for key in (
        "contract_version", "delivery_id", "correlation_id", "source_issue",
        "target_repository", "requested_branch", "concurrency_group", "instructions",
    )}
    fingerprint = hashlib.sha256(json.dumps(immutable, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    ledger_path = os.environ.get("ROUTER_DELIVERY_LEDGER")
    if ledger_path:
        ledger_file = Path(ledger_path)
        try:
            ledger = json.loads(ledger_file.read_text(encoding="utf-8")) if ledger_file.exists() else {}
        except (OSError, json.JSONDecodeError) as exc:
            reject("publication", f"Router delivery ledger cannot be read safely: {exc}", correlation_id)
        existing = ledger.get(delivery_id)
        if existing and existing.get("fingerprint") != fingerprint:
            reject("contract-validation", "Delivery ID was reused with different immutable payload fields.", correlation_id)
        if existing:
            output("execution_result", "duplicate-delivery")
            output("routing_status", "duplicate-delivery")
            output("correlation_id", correlation_id)
            output("delivery_id", delivery_id)
            output("generated_branch", execution["requested_branch"])
            output("diagnostic_summary", "Duplicate canonical delivery matched prior immutable routing metadata.")
            return
    payload = json.dumps(execution, separators=(",", ":"), sort_keys=True)
    cmd = [
        "gh", "workflow", "run", workflow_path,
        "--repo", target_repository,
        "--ref", ref,
        "-f", f"execution_input_json={payload}",
        "-f", f"concurrency_group={concurrency_group}",
    ]
    try:
        subprocess.run(cmd, check=True, text=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", None) or getattr(exc, "stdout", None) or str(exc)
        reject("publication", f"Target workflow dispatch failed: {detail}", correlation_id)
    if ledger_path:
        ledger[delivery_id] = {"fingerprint": fingerprint, "target_repository": target_repository, "requested_branch": execution["requested_branch"]}
        try:
            ledger_file.parent.mkdir(parents=True, exist_ok=True)
            ledger_file.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except OSError as exc:
            reject("publication", f"Router delivery ledger cannot be written safely: {exc}", correlation_id)
    output("execution_result", "dispatched")
    output("routing_status", "dispatched")
    output("correlation_id", correlation_id)
    output("delivery_id", delivery_id)
    output("generated_branch", execution["requested_branch"])
    output("diagnostic_summary", "Canonical execution input dispatched to the registered workflow.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"validate", "dispatch", "validate-registry"}:
        print("Usage: codex_router.py validate|dispatch|validate-registry", file=sys.stderr)
        raise SystemExit(2)
    if sys.argv[1] == "validate":
        validate()
    elif sys.argv[1] == "dispatch":
        dispatch()
    else:
        validate_registry()
        print("Registry validation passed.")
