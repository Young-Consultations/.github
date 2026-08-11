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

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised in minimal local environments
    yaml = None  # type: ignore[assignment]

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


if yaml is not None:
    class GithubSafeLoader(yaml.SafeLoader):
        """Safe YAML loader which does not interpret GitHub's `on` key as boolean."""
else:
    GithubSafeLoader = None  # type: ignore[assignment]


def debug(message: str) -> None:
    """Emit CI-visible diagnostics without including credentials."""
    print(f"[target-workflow-verifier] {message}", file=sys.stderr, flush=True)


# PyYAML implements YAML 1.1, where "on" is a boolean. GitHub uses YAML 1.2.
if yaml is not None and GithubSafeLoader is not None:
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


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CompatibilityError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_registry(path: Path = REGISTRY) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, json.JSONDecodeError, CompatibilityError) as exc:
        raise CompatibilityError(f"registry cannot be loaded: {exc}") from exc
    repositories = data.get("repositories") if isinstance(data, dict) else None
    if not isinstance(data, dict) or data.get("registry_format_version") != 1:
        raise CompatibilityError("unsupported registry_format_version")
    if not isinstance(repositories, dict):
        raise CompatibilityError("registry must contain a repositories mapping")
    for repository, entry in repositories.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("enabled"), bool):
            raise CompatibilityError(f"invalid registry entry: {repository}")
        if entry.get("draft_pr_only") is not True:
            raise CompatibilityError(f"{repository}: draft-only publication required")
        if not isinstance(entry.get("max_parallel_tasks"), int) or entry["max_parallel_tasks"] < 1:
            raise CompatibilityError(f"{repository}: deterministic concurrency policy required")
        workflow_repository, workflow_path, workflow_revision = parse_workflow_ref(entry.get("workflow_ref"))
        if entry["enabled"] and not re.fullmatch(r"[0-9a-f]{40}", workflow_revision):
            raise CompatibilityError(f"{repository}: enabled workflow_ref must use an immutable revision")
        if workflow_repository != repository:
            raise CompatibilityError(f"{repository}: workflow_ref repository mismatch")
        if workflow_path in {".github/workflows/codex-router.yml", ".github/workflows/router-smoke-test.yml", ".github/workflows/issue-to-codex.yml"}:
            raise CompatibilityError(f"{repository}: obsolete workflow_ref is not allowed")
        idempotency = entry.get("idempotency")
        if not isinstance(idempotency, dict) or idempotency.get("branch_identity") != "delivery_id" or idempotency.get("ownership_marker") != "ai-sdlc-delivery-id" or idempotency.get("requires_preflight") is not True or idempotency.get("requires_fail_closed_reuse") is not True or idempotency.get("requires_create_race_requery") is not True:
            raise CompatibilityError(f"{repository}: target idempotency policy is incomplete")
        if entry.get("contract_version") != CANONICAL_VERSION:
            raise CompatibilityError(f"{repository}: contract-version mismatch")
    return repositories


def _parse_scalar(value: str) -> Any:
    value = value.strip().strip('"\'')
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def _parse_inline_mapping(value: str) -> dict[str, Any]:
    value = value.strip()
    if not (value.startswith("{") and value.endswith("}")):
        return {}
    result: dict[str, Any] = {}
    for item in value[1:-1].split(","):
        if ":" not in item:
            continue
        key, raw = item.split(":", 1)
        result[key.strip()] = _parse_scalar(raw)
    return result


def _parse_workflow_without_yaml(source: str) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    in_inputs = False
    current: str | None = None
    has_dispatch = "workflow_dispatch:" in source
    for line in source.splitlines():
        stripped = line.strip()
        if stripped == "inputs:":
            in_inputs = True
            continue
        if not in_inputs or not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= 4 and not stripped.startswith(("required:", "type:")):
            current = None
            if not stripped.endswith(":"):
                in_inputs = False
            continue
        if stripped.endswith(":") and not stripped.startswith(("required:", "type:")):
            current = stripped[:-1]
            inputs[current] = {}
        elif ":" in stripped and not stripped.startswith(("required:", "type:")):
            name, raw = stripped.split(":", 1)
            current = name.strip()
            inputs[current] = _parse_inline_mapping(raw)
        elif current and ":" in stripped:
            key, raw = stripped.split(":", 1)
            inputs[current][key.strip()] = _parse_scalar(raw)
    return {"on": {"workflow_dispatch": {"inputs": inputs}}} if has_dispatch else {"on": {}}


def parse_workflow(source: str) -> dict[str, Any]:
    if yaml is None:
        return _parse_workflow_without_yaml(source)
    try:
        document = yaml.load(source, Loader=GithubSafeLoader)
    except yaml.YAMLError as exc:
        raise CompatibilityError(f"invalid workflow YAML: {exc}") from exc
    if not isinstance(document, dict):
        raise CompatibilityError("workflow must be a YAML mapping")
    return document


def verify_idempotency_capability(source: str) -> None:
    lowered = source.lower()
    if "delivery_id" not in lowered:
        raise CompatibilityError("canonical delivery_id is omitted")
    forbidden = ("github.run_id", "github.run_attempt", "date +", "uuidgen", "random", "$random")
    for token in forbidden:
        if token in lowered:
            raise CompatibilityError("branch identity must not derive from run id, attempts, timestamps, or random data")
    required_tokens = {
        "preflight": "target-side idempotency preflight capability is missing",
        "ai-sdlc-delivery-id": "machine-readable ownership marker containing delivery_id is missing",
        "ownership marker": "pull-request ownership validation is missing",
        "draft": "draft pull-request enforcement is missing",
        "fail-closed": "ambiguous or unsafe reuse must fail closed",
        "create-race": "create-race recovery by re-querying after conflict is missing",
        "duplicate-reused": "canonical reuse execution result is missing",
    }
    for token, message in required_tokens.items():
        if token not in lowered:
            raise CompatibilityError(message)


def verify_interface(source: str) -> str:
    workflow = parse_workflow(source)
    triggers = workflow.get("on")
    dispatch = triggers.get("workflow_dispatch") if isinstance(triggers, dict) else None
    if not isinstance(dispatch, dict):
        raise CompatibilityError("workflow_dispatch is missing")
    inputs = dispatch.get("inputs")
    if not isinstance(inputs, dict):
        raise CompatibilityError("workflow_dispatch.inputs is missing")
    for name in EXPECTED_INPUTS:
        if name not in inputs:
            raise CompatibilityError(f"missing {name}")
    for name, (required, input_type) in EXPECTED_INPUTS.items():
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
        if name in inputs
    )
    if obsolete:
        raise CompatibilityError("obsolete v1 field-by-field interface is not allowed: " + ", ".join(obsolete))
    required_names = {name for name, definition in inputs.items() if isinstance(definition, dict) and definition.get("required") is True}
    incompatible_required = sorted(required_names - {"concurrency_group"})
    if incompatible_required:
        raise CompatibilityError("incompatible required workflow_dispatch inputs: " + ", ".join(incompatible_required))
    verify_idempotency_capability(source)
    return "canonical v2 JSON + idempotent consumer"


def fetch_workflow(repository: str, path: str, ref: str, token: str | None = None) -> str:
    quoted_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
    url = f"https://api.github.com/repos/{repository}/contents/{quoted_path}?ref={urllib.parse.quote(ref, safe='')}"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    debug(f"requesting {url} (authentication: {'configured' if token else 'not configured'})")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        status = f"HTTP {exc.code}: " if isinstance(exc, urllib.error.HTTPError) else ""
        safe_reason = str(getattr(exc, "reason", exc))
        safe_reason = re.sub(r"gh[pousr]_[A-Za-z0-9_]+", "[redacted-token]", safe_reason)
        safe_reason = re.sub(r"(?i)(authorization|token|secret|password)[:=][^\s,]+", r"\1=[redacted]", safe_reason)
        raise CompatibilityError(
            f"workflow is unavailable at registered ref ({url}): "
            f"{status}{safe_reason}"
        ) from exc
    try:
        # GitHub's Contents API wraps Base64 content across multiple lines.
        encoded_content = "".join(payload["content"].split())
        source = base64.b64decode(encoded_content, validate=True).decode("utf-8")
        debug(f"received {len(source.encode('utf-8'))} decoded bytes for {repository}/{path}@{ref}")
        return source
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise CompatibilityError("GitHub returned invalid workflow content") from exc


def verify_registry(
    repositories: dict[str, dict[str, Any]], token: str | None, selected_repository: str | None = None
) -> list[dict[str, str]]:
    report = []
    for repository, entry in repositories.items():
        if selected_repository is not None and repository != selected_repository:
            continue
        if not entry["enabled"] and selected_repository is None:
            debug(f"skipping disabled target {repository}")
            continue
        workflow_repository, path, ref = parse_workflow_ref(entry["workflow_ref"])
        debug(f"checking {repository}: {path}@{ref}")
        row = {"repository": repository, "workflow": path, "ref": ref,
               "contract_version": entry["contract_version"], "draft_pr_only": str(entry["draft_pr_only"]).lower(),
               "transport_interface": "unknown", "result": "pass"}
        try:
            row["transport_interface"] = verify_interface(fetch_workflow(workflow_repository, path, ref, token))
            if ref in {"main", "master"}:
                row["result"] = "pass (warning: movable ref)"
        except CompatibilityError as exc:
            row["result"] = f"fail: {exc}"
        debug(f"{repository}: {row['result']} ({row['transport_interface']})")
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
        debug(f"appended compatibility table to {summary}")
    # Keep the result visible in the job log even when Actions also has a step summary.
    print("\n".join(lines), flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--report", type=Path, default=ROOT / "reports/target-workflow-compatibility.json")
    parser.add_argument("--fixtures-only", action="store_true", help="validate the canonical local target fixture without network access")
    parser.add_argument("--repository", help="validate one registered repository, including when it is disabled")
    args = parser.parse_args(argv)
    try:
        repositories = load_registry(args.registry)
        debug(f"loaded {len(repositories)} registry entries from {args.registry}")
        if args.fixtures_only:
            fixture = ROOT / "tests/fixtures/target_workflows/portfolio-tasks-codex-execute.yml"
            interface = verify_interface(fixture.read_text(encoding="utf-8"))
            report = [{"repository": "Young-Consultations/portfolio-tasks", "workflow": ".github/workflows/codex-execute.yml",
                       "ref": "fixture", "contract_version": CANONICAL_VERSION, "draft_pr_only": "true", "transport_interface": interface, "result": "pass"}]
        else:
            token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
            if args.repository and args.repository not in repositories:
                raise CompatibilityError(f"{args.repository}: repository is not registered")
            report = verify_registry(repositories, token, args.repository)
        write_outputs(report, args.report)
        failed = sum(row["result"].startswith("fail") for row in report)
        debug(f"wrote report to {args.report}; checked={len(report)}, failed={failed}")
        return int(bool(failed))
    except (CompatibilityError, OSError) as exc:
        print(f"compatibility verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
