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
ACTIVATION = Path(
    os.environ.get("CODEX_ACTIVATION_PATH", ROOT / "config/codex-activation.json")
)
TASK_SCHEMA = ROOT / "contracts/task-contract.schema.json"
INPUT_SCHEMA = ROOT / "contracts/execution-input.schema.json"
RELEASE_MANIFEST = ROOT / "release/release-manifest.json"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_RE = re.compile(r"[^a-z0-9._-]+")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
REPORT_PATH_RE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+\.json$")
# workflow_dispatch accepts only a branch or tag for --ref. Adapter release tags
# use this governed, non-moving namespace so dispatchability and immutability
# are enforced together.
IMMUTABLE_ADAPTER_TAG_RE = re.compile(
    r"codex-adapter-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
)
CONTROL_PLANE_TAG_RE = re.compile(
    r"ai-sdlc-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
)
ADMISSION_RE = re.compile(r"<!-- ai-sdlc-admission:v2 (\{[^\n]*\}) -->")
FAILURE_CATEGORIES = {
    "contract-validation", "authorization", "dependency",
    "repository-routing", "publication", "unknown",
}
REGISTRY_FIELDS = {
    "workflow_ref", "allowed_task_types", "codex_environment",
    "max_parallel_tasks", "draft_pr_only", "contract_version", "conformance",
    "idempotency",
}
CONFORMANCE_FIELDS = {
    "fixture_set", "fixture_version", "compatibility_sha", "adapter_ref",
    "adapter_commit_sha", "report_path", "report_sha256", "status",
    "activation_evidence_sufficient",
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


def validate_conformance(
    repository: str, entry: dict[str, Any], *, required: bool,
) -> bool:
    """Validate reviewed shared-oracle evidence recorded in the capability snapshot."""
    evidence = entry.get("conformance")
    if evidence is None:
        if required:
            reject(
                "repository-routing",
                f"Enabled target {repository} has no reviewed TC-MVP-CI-001 evidence.",
            )
        return False
    if not isinstance(evidence, dict) or set(evidence) != CONFORMANCE_FIELDS:
        reject("repository-routing", f"Registry entry {repository} has invalid conformance evidence.")
    _, adapter_ref = parse_workflow_ref(repository, entry.get("workflow_ref"))
    fixture_version = read_json(RELEASE_MANIFEST).get("fixture_version")
    valid = (
        evidence.get("fixture_set") == "TC-MVP-CI-001"
        and evidence.get("fixture_version") == fixture_version
        and evidence.get("adapter_ref") == adapter_ref
        and isinstance(evidence.get("compatibility_sha"), str)
        and SHA_RE.fullmatch(evidence["compatibility_sha"]) is not None
        and isinstance(evidence.get("adapter_commit_sha"), str)
        and SHA_RE.fullmatch(evidence["adapter_commit_sha"]) is not None
        and isinstance(evidence.get("report_path"), str)
        and REPORT_PATH_RE.fullmatch(evidence["report_path"]) is not None
        and isinstance(evidence.get("report_sha256"), str)
        and DIGEST_RE.fullmatch(evidence["report_sha256"]) is not None
        and evidence.get("status") == "pass"
        and evidence.get("activation_evidence_sufficient") is True
    )
    if not valid:
        reject("repository-routing", f"Registry entry {repository} has invalid conformance evidence.")
    return True


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
        if not isinstance(entry["draft_pr_only"], bool):
            reject("repository-routing", f"Registry entry {name} has invalid boolean policy.")
        if entry["draft_pr_only"] is not True:
            reject("repository-routing", f"Registry entry {name} must enforce draft_pr_only.")
        if not isinstance(entry["max_parallel_tasks"], int) or entry["max_parallel_tasks"] < 1:
            reject("repository-routing", f"Registry entry {name} has invalid max_parallel_tasks.")
        if not isinstance(entry["allowed_task_types"], list) or not entry["allowed_task_types"] or not set(entry["allowed_task_types"]) <= supported_types:
            reject("repository-routing", f"Registry entry {name} has invalid allowed_task_types.")
        parse_workflow_ref(name, entry["workflow_ref"])
        if not isinstance(entry["codex_environment"], str) or not entry["codex_environment"]:
            reject("repository-routing", f"Registry entry {name} has an invalid codex_environment.")
        idempotency = entry.get("idempotency")
        if not isinstance(idempotency, dict) or idempotency.get("branch_identity") != "delivery_id" or idempotency.get("ownership_marker") != "ai-sdlc-delivery-id" or idempotency.get("requires_preflight") is not True or idempotency.get("requires_fail_closed_reuse") is not True or idempotency.get("requires_create_race_requery") is not True or idempotency.get("terminal_reuse_status") != "duplicate-reused":
            reject("repository-routing", f"Registry entry {name} lacks required target idempotency policy.")
        if entry["contract_version"] != read_json(INPUT_SCHEMA)["properties"]["contract_version"]["const"]:
            reject("repository-routing", f"Registry entry {name} has an unsupported contract_version.")
        validate_conformance(name, entry, required=False)
    return repositories


def validate_activation(repositories: dict[str, Any]) -> dict[str, bool]:
    """Load current control-plane activation independently of capabilities."""
    try:
        data = read_json(ACTIVATION)
    except (OSError, json.JSONDecodeError) as exc:
        reject("repository-routing", f"Activation state cannot be loaded: {exc}")
    targets = data.get("targets")
    if data.get("activation_format_version") != 1 or not isinstance(targets, dict):
        reject("repository-routing", "Activation state must declare supported activation_format_version 1.")
    if set(targets) != set(repositories) or any(not isinstance(value, bool) for value in targets.values()):
        reject("repository-routing", "Activation state must contain one boolean for every registered target.")
    return targets


def routing_configuration() -> tuple[dict[str, Any], dict[str, bool]]:
    repositories = validate_registry()
    activation = validate_activation(repositories)
    for name, enabled in activation.items():
        _, revision = parse_workflow_ref(name, repositories[name]["workflow_ref"])
        if enabled and not IMMUTABLE_ADAPTER_TAG_RE.fullmatch(revision):
            reject(
                "repository-routing",
                f"Enabled target {name} must use a governed immutable codex-adapter-v* release tag.",
            )
        if enabled:
            if repositories[name]["max_parallel_tasks"] != 1:
                reject(
                    "repository-routing",
                    f"Enabled target {name} must declare max_parallel_tasks 1 in the v2 runtime.",
                )
            validate_conformance(name, repositories[name], required=True)
    return repositories, activation


def routing_evidence() -> dict[str, str]:
    """Return the immutable release and exact mutable activation snapshot identity."""
    evidence = {
        "control_plane_release": os.environ.get("CONTROL_PLANE_RELEASE", ""),
        "activation_revision": os.environ.get("CODEX_ACTIVATION_REVISION", ""),
        "activation_sha256": os.environ.get("CODEX_ACTIVATION_SHA256", ""),
    }
    if CONTROL_PLANE_TAG_RE.fullmatch(evidence["control_plane_release"]) is None:
        reject("repository-routing", "Control-plane release identity is missing or invalid.")
    if SHA_RE.fullmatch(evidence["activation_revision"]) is None:
        reject("repository-routing", "Activation revision identity is missing or invalid.")
    if DIGEST_RE.fullmatch(evidence["activation_sha256"]) is None:
        reject("repository-routing", "Activation content digest is missing or invalid.")
    return evidence


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
    repositories, activation = routing_configuration()
    route_evidence = routing_evidence()
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
    if not activation[target]:
        reject("repository-routing", f"Repository {target} is disabled.", correlation_id)
    if task["task_type"] not in entry["allowed_task_types"]:
        reject("repository-routing", f"Task type {task['task_type']} is not allowed for {target}.", correlation_id)
    if task["contract_version"] != entry["contract_version"]:
        reject("contract-validation", "Task contract version is not supported by the target.", correlation_id)

    # The only enabled REAL path is intentionally serialized per target. The
    # v2 parallel_safe field remains contract data, not an unenforced promise.
    group = (
        f"codex-{slug(target)}-real"
        if execution_mode == "implement"
        else f"codex-{slug(target)}-verify-{slug(task['source_issue'])}"
    )
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
        **route_evidence,
    }
    for key, value in values.items():
        output(key, value)
    return values


def _github_json(*args: str) -> Any:
    completed = subprocess.run(
        ["gh", "api", *args], check=True, text=True, capture_output=True,
    )
    if not completed.stdout.strip():
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("GitHub API returned invalid JSON") from exc


def _existing_admissions(repository: str, issue: str, delivery_id: str) -> list[dict[str, Any]]:
    pages = _github_json(
        "--paginate", "--slurp",
        f"repos/{repository}/issues/{issue}/comments?per_page=100",
    )
    if not isinstance(pages, list):
        raise ValueError("GitHub issue comment response is not a list")
    comments = [item for page in pages for item in page] if all(isinstance(page, list) for page in pages) else pages
    admissions: list[dict[str, Any]] = []
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        user = comment.get("user")
        author = user.get("login") if isinstance(user, dict) else None
        if not isinstance(author, str) or not author:
            continue
        for match in ADMISSION_RE.finditer(str(comment.get("body", ""))):
            try:
                value = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and value.get("delivery_id") == delivery_id:
                admissions.append({"author": author, "binding": value})
    return admissions


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

    repositories, activation = routing_configuration()
    route_evidence = routing_evidence()
    target_repository = execution["target_repository"]
    entry = repositories.get(target_repository)
    if entry is None:
        reject("repository-routing", f"Repository {target_repository} is not registered.", correlation_id)
    if not activation[target_repository]:
        reject("repository-routing", f"Repository {target_repository} is disabled.", correlation_id)
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
    issue_match = re.fullmatch(r"([^#]+)#([1-9][0-9]*)", execution["source_issue"])
    if not issue_match:
        reject("contract-validation", "Execution input source issue is malformed.", correlation_id)
    binding = {key: execution[key] for key in (
        "contract_version", "delivery_id", "correlation_id", "source_issue", "target_repository",
    )}
    binding.update(route_evidence)
    admission_body = "<!-- ai-sdlc-admission:v2 " + json.dumps(
        binding, separators=(",", ":"), sort_keys=True
    ) + " -->"
    cmd = [
        "gh", "workflow", "run", workflow_path,
        "--repo", target_repository,
        "--ref", ref,
        "-f", f"execution_input_json={payload}",
        "-f", f"concurrency_group={concurrency_group}",
    ]
    try:
        existing = _existing_admissions(
            issue_match.group(1), issue_match.group(2), delivery_id,
        )
        posted = _github_json(
            f"repos/{issue_match.group(1)}/issues/{issue_match.group(2)}/comments",
            "--method", "POST", "-f", f"body={admission_body}",
        )
        posted_user = posted.get("user") if isinstance(posted, dict) else None
        author = posted_user.get("login") if isinstance(posted_user, dict) else None
        posted_id = posted.get("id") if isinstance(posted, dict) else None
        if not isinstance(author, str) or not author:
            raise ValueError("Admission response did not identify the router credential")
        if not isinstance(posted_id, int):
            raise ValueError("Admission response did not identify the created journal comment")
        owned = [item["binding"] for item in existing if item["author"] == author]
        if any(item != binding for item in owned):
            _github_json(
                f"repos/{issue_match.group(1)}/issues/comments/{posted_id}",
                "--method", "DELETE",
            )
            reject("authorization", "Conflicting admission journal exists for this delivery.", correlation_id)
        if owned:
            _github_json(
                f"repos/{issue_match.group(1)}/issues/comments/{posted_id}",
                "--method", "DELETE",
            )
        subprocess.run(cmd, check=True, text=True, capture_output=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
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
        routing_configuration()
        print("Capability registry and activation validation passed.")
