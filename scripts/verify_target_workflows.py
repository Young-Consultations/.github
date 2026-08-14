#!/usr/bin/env python3
"""Read-only verification of registered target workflow dispatch interfaces."""
from __future__ import annotations

import argparse
import base64
import hashlib
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
ACTIVATION = ROOT / "config/codex-activation.json"
RELEASE_MANIFEST = ROOT / "release/release-manifest.json"
FIXTURE_MANIFEST = ROOT / "tests/fixtures/mvp-v2/manifest.json"
CANONICAL_VERSION = "ai-sdlc-contract/v2"
EXPECTED_INPUTS = {
    "execution_input_json": (True, "string"),
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
IMMUTABLE_ADAPTER_TAG_RE = re.compile(
    r"codex-adapter-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
)
IMMUTABLE_RECEIVER_REF_RE = re.compile(
    r"(?:[0-9a-f]{40}|ai-sdlc-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?)"
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
REPORT_PATH_RE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+\.json$")
FILE_PATH_RE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+$")
PIN_REVISION_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_BLOB_RE = re.compile(r"^[0-9a-f]{40}$")
CONFORMANCE_PIN_PATH = "config/mvp-conformance-pin.json"
CONFORMANCE_PIN_FIELDS = {
    "pin_format_version", "organization_repository", "compatibility_sha",
    "fixture_set", "fixture_version", "adapter_revision",
    "compatibility_files", "target_files",
}
PINNED_COMPATIBILITY_FILES = {
    "contracts/task-contract.schema.json",
    "contracts/execution-input.schema.json",
    "contracts/execution-result.schema.json",
    "tests/fixtures/mvp-v2/manifest.json",
    "tests/fixtures/mvp-v2/scenarios.json",
    "tests/fixtures/mvp-v2/expected-results.json",
}
CONFORMANCE_FIELDS = {
    "fixture_set", "fixture_version", "compatibility_sha", "adapter_ref",
    "adapter_commit_sha", "report_path", "report_sha256", "status",
    "activation_evidence_sufficient",
}
RECEIVER_REF_RE = re.compile(
    r"Young-Consultations/\.github/\.github/workflows/"
    r"codex-result-receiver\.yml@([^\s#]+)"
)
RECEIVER_ACTION_RE = re.compile(
    r"Young-Consultations/\.github/actions/codex-result-receiver@([^\s#]+)"
)
AUTHOR_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*(?:\[bot\])?$")
REQUIRED_ZERO_EFFECTS = {
    "codex_calls", "real_branches_created", "real_commits_created",
    "real_pushes", "real_pull_requests_created", "merge_actions",
    "release_actions", "deployment_actions", "production_actions",
    "secret_outputs",
}


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


def release_fixture_version() -> str:
    try:
        manifest = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompatibilityError(f"release manifest cannot be loaded: {exc}") from exc
    version = manifest.get("fixture_version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not version:
        raise CompatibilityError("release fixture_version is missing")
    return version


def git_blob_sha1(data: bytes) -> str:
    """Return the Git blob identity for exact bytes without needing a checkout."""
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def conformance_pin_revision(pin: dict[str, Any]) -> str:
    """Bind a pin without recursively hashing its own revision field."""
    material = dict(pin)
    material["adapter_revision"] = None
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def validate_conformance_record(
    repository: str, entry: dict[str, Any], *, required: bool,
) -> dict[str, Any] | None:
    evidence = entry.get("conformance")
    if evidence is None:
        if required:
            raise CompatibilityError(f"{repository}: reviewed TC-MVP-CI-001 evidence is missing")
        return None
    if not isinstance(evidence, dict) or set(evidence) != CONFORMANCE_FIELDS:
        raise CompatibilityError(f"{repository}: conformance evidence has an invalid shape")
    workflow_ref = parse_workflow_ref(entry.get("workflow_ref"))[2]
    valid = (
        evidence.get("fixture_set") == "TC-MVP-CI-001"
        and evidence.get("fixture_version") == release_fixture_version()
        and evidence.get("adapter_ref") == workflow_ref
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
        raise CompatibilityError(f"{repository}: conformance evidence is invalid")
    return evidence


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
        if not isinstance(entry, dict):
            raise CompatibilityError(f"invalid registry entry: {repository}")
        if entry.get("draft_pr_only") is not True:
            raise CompatibilityError(f"{repository}: draft-only publication required")
        if not isinstance(entry.get("max_parallel_tasks"), int) or entry["max_parallel_tasks"] < 1:
            raise CompatibilityError(f"{repository}: deterministic concurrency policy required")
        workflow_repository, workflow_path, workflow_revision = parse_workflow_ref(entry.get("workflow_ref"))
        if workflow_repository != repository:
            raise CompatibilityError(f"{repository}: workflow_ref repository mismatch")
        if workflow_path in {".github/workflows/codex-router.yml", ".github/workflows/router-smoke-test.yml", ".github/workflows/issue-to-codex.yml"}:
            raise CompatibilityError(f"{repository}: obsolete workflow_ref is not allowed")
        idempotency = entry.get("idempotency")
        if not isinstance(idempotency, dict) or idempotency.get("branch_identity") != "delivery_id" or idempotency.get("ownership_marker") != "ai-sdlc-delivery-id" or idempotency.get("requires_preflight") is not True or idempotency.get("requires_fail_closed_reuse") is not True or idempotency.get("requires_create_race_requery") is not True:
            raise CompatibilityError(f"{repository}: target idempotency policy is incomplete")
        if entry.get("contract_version") != CANONICAL_VERSION:
            raise CompatibilityError(f"{repository}: contract-version mismatch")
        if "conformance" not in entry:
            raise CompatibilityError(f"{repository}: conformance evidence field is missing")
        validate_conformance_record(repository, entry, required=False)
    return repositories


def load_activation(path: Path, repositories: dict[str, dict[str, Any]]) -> dict[str, bool]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, json.JSONDecodeError, CompatibilityError) as exc:
        raise CompatibilityError(f"activation state cannot be loaded: {exc}") from exc
    targets = data.get("targets") if isinstance(data, dict) else None
    if data.get("activation_format_version") != 1 or not isinstance(targets, dict):
        raise CompatibilityError("unsupported activation_format_version")
    if set(targets) != set(repositories) or any(not isinstance(value, bool) for value in targets.values()):
        raise CompatibilityError("activation state must contain one boolean for every registered target")
    for repository, enabled in targets.items():
        revision = parse_workflow_ref(repositories[repository]["workflow_ref"])[2]
        if enabled and not IMMUTABLE_ADAPTER_TAG_RE.fullmatch(revision):
            raise CompatibilityError(
                f"{repository}: enabled workflow_ref must use a governed immutable codex-adapter-v* release tag"
            )
        if enabled:
            validate_conformance_record(repository, repositories[repository], required=True)
    return targets


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


def verify_receiver_compatibility(source: str) -> str:
    workflow = parse_workflow(source)
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        raise CompatibilityError("target jobs are missing")
    receiver_jobs: list[tuple[dict[str, Any], str]] = []
    for job in jobs.values():
        if not isinstance(job, dict) or not isinstance(job.get("uses"), str):
            continue
        if match := RECEIVER_REF_RE.fullmatch(job["uses"]):
            receiver_jobs.append((job, match.group(1)))
    if len(receiver_jobs) != 1:
        raise CompatibilityError("exactly one canonical result-receiver call is required")
    receiver_job, receiver_ref = receiver_jobs[0]
    if not IMMUTABLE_RECEIVER_REF_RE.fullmatch(receiver_ref):
        raise CompatibilityError("result receiver must use an immutable ai-sdlc release or full commit SHA")
    receiver_inputs = receiver_job.get("with")
    if not isinstance(receiver_inputs, dict) or set(receiver_inputs) != {
        "execution_result", "source_issue",
    }:
        raise CompatibilityError("result receiver call must supply exactly execution_result and source_issue")
    if "CODEX_TRUSTED_JOURNAL_AUTHORS" in source:
        raise CompatibilityError("target must not supply control-plane journal-author policy")
    receiver_secrets = receiver_job.get("secrets")
    if not isinstance(receiver_secrets, dict) or set(receiver_secrets) != {"CODEX_RESULT_TOKEN"}:
        raise CompatibilityError("result receiver call must supply only CODEX_RESULT_TOKEN")
    if not isinstance(receiver_secrets["CODEX_RESULT_TOKEN"], str) or not receiver_secrets["CODEX_RESULT_TOKEN"].strip():
        raise CompatibilityError("result-only delivery credential is missing")
    return receiver_ref


def verify_receiver_interface(source: str) -> str:
    workflow = parse_workflow(source)
    triggers = workflow.get("on")
    call = triggers.get("workflow_call") if isinstance(triggers, dict) else None
    if not isinstance(call, dict):
        raise CompatibilityError("result receiver workflow_call interface is missing")
    inputs = call.get("inputs")
    secrets = call.get("secrets")
    if not isinstance(inputs, dict) or set(inputs) != {"execution_result", "source_issue"}:
        raise CompatibilityError("result receiver inputs are incompatible")
    for name, definition in inputs.items():
        if not isinstance(definition, dict) or definition.get("required") is not True or definition.get("type") != "string":
            raise CompatibilityError(f"result receiver input {name} must be a required string")
    if not isinstance(secrets, dict) or set(secrets) != {"CODEX_RESULT_TOKEN"}:
        raise CompatibilityError("result receiver must accept only CODEX_RESULT_TOKEN")
    token = secrets["CODEX_RESULT_TOKEN"]
    if not isinstance(token, dict) or token.get("required") is not True:
        raise CompatibilityError("result receiver CODEX_RESULT_TOKEN must be required")
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        raise CompatibilityError("result receiver jobs are missing")
    action_steps: list[tuple[dict[str, Any], str]] = []
    for job in jobs.values():
        steps = job.get("steps") if isinstance(job, dict) else None
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict) or not isinstance(step.get("uses"), str):
                continue
            if match := RECEIVER_ACTION_RE.fullmatch(step["uses"]):
                action_steps.append((step, match.group(1)))
    if len(action_steps) != 1:
        raise CompatibilityError("result receiver must invoke exactly one canonical control-plane action bundle")
    action_step, action_ref = action_steps[0]
    if not IMMUTABLE_RECEIVER_REF_RE.fullmatch(action_ref):
        raise CompatibilityError("result receiver action bundle must use an immutable ai-sdlc release or full commit SHA")
    expected_with = {
        "result-token": "${{ secrets.CODEX_RESULT_TOKEN }}",
        "execution-result": "${{ inputs.execution_result }}",
        "source-issue": "${{ inputs.source_issue }}",
        "caller-repository": "${{ github.repository }}",
    }
    if action_step.get("with") != expected_with or "env" in action_step:
        raise CompatibilityError("result receiver action inputs are incompatible")
    if "actions/checkout@" in source:
        raise CompatibilityError("result receiver must not checkout caller-controlled policy content")
    return action_ref


def verify_receiver_action(source: str) -> None:
    action = parse_workflow(source)
    inputs = action.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "result-token", "execution-result", "source-issue", "caller-repository",
    }:
        raise CompatibilityError("result receiver action inputs are incompatible")
    if any(
        not isinstance(definition, dict) or definition.get("required") is not True
        for definition in inputs.values()
    ):
        raise CompatibilityError("result receiver action inputs must be required")
    runs = action.get("runs")
    steps = runs.get("steps") if isinstance(runs, dict) else None
    if not isinstance(runs, dict) or runs.get("using") != "composite" or not isinstance(steps, list):
        raise CompatibilityError("result receiver action must be a composite action")
    commands = "\n".join(
        step.get("run", "") for step in steps
        if isinstance(step, dict) and isinstance(step.get("run"), str)
    )
    if any(not isinstance(step, dict) or step.get("shell") != "bash" for step in steps):
        raise CompatibilityError("result receiver action steps must use bash explicitly")
    if "actions/checkout@" in source or "CODEX_TRUSTED_JOURNAL_AUTHORS" in source:
        raise CompatibilityError("result receiver action contains a caller-controlled boundary")
    if "jsonschema[format]" not in commands:
        raise CompatibilityError("result receiver action omits schema validator installation")
    if 'python3 "$GITHUB_ACTION_PATH/../../scripts/codex_result_receiver.py"' not in commands:
        raise CompatibilityError("result receiver action does not execute its own immutable receiver bundle")
    receiver_steps = [
        step for step in steps
        if isinstance(step, dict)
        and isinstance(step.get("run"), str)
        and "codex_result_receiver.py" in step["run"]
    ]
    expected_env = {
        "GH_TOKEN": "${{ inputs.result-token }}",
        "EXECUTION_RESULT": "${{ inputs.execution-result }}",
        "SOURCE_ISSUE": "${{ inputs.source-issue }}",
        "CALLER_REPOSITORY": "${{ inputs.caller-repository }}",
    }
    if len(receiver_steps) != 1 or receiver_steps[0].get("env") != expected_env:
        raise CompatibilityError("result receiver action does not isolate its credential and payload environment")
    if any("env" in step for step in steps if step is not receiver_steps[0]):
        raise CompatibilityError("result receiver action exposes receiver environment to another step")


def verify_receiver_bundle_policy(script: str, policy_raw: bytes) -> None:
    if 'TRUST_POLICY = ROOT / "config/codex-result-trust.json"' not in script:
        raise CompatibilityError("result receiver does not load control-plane trust policy")
    if "CODEX_TRUSTED_JOURNAL_AUTHORS" in script:
        raise CompatibilityError("result receiver reads caller-controlled journal-author policy")
    try:
        policy = json.loads(policy_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CompatibilityError("result receiver trust policy is not valid JSON") from exc
    authors = policy.get("trusted_journal_authors") if isinstance(policy, dict) else None
    valid = (
        isinstance(policy, dict)
        and set(policy) == {"policy_format_version", "trusted_journal_authors"}
        and policy.get("policy_format_version") == 1
        and isinstance(authors, list)
        and bool(authors)
        and all(isinstance(author, str) and AUTHOR_RE.fullmatch(author) for author in authors)
        and len({author.casefold() for author in authors}) == len(authors)
    )
    if not valid:
        raise CompatibilityError("result receiver trust policy is not a reviewed non-empty allowlist")


def verify_interface(source: str) -> str:
    workflow = parse_workflow(source)
    triggers = workflow.get("on")
    dispatch = triggers.get("workflow_dispatch") if isinstance(triggers, dict) else None
    if not isinstance(dispatch, dict):
        raise CompatibilityError("workflow_dispatch is missing")
    inputs = dispatch.get("inputs")
    if not isinstance(inputs, dict):
        raise CompatibilityError("workflow_dispatch.inputs is missing")
    missing = sorted(set(EXPECTED_INPUTS) - set(inputs))
    unexpected = sorted(set(inputs) - set(EXPECTED_INPUTS))
    if missing:
        raise CompatibilityError("missing " + ", ".join(missing))
    if unexpected:
        raise CompatibilityError(
            "workflow_dispatch must declare exactly execution_input_json and concurrency_group; "
            "unexpected inputs: " + ", ".join(unexpected)
        )
    for name, (required, input_type) in EXPECTED_INPUTS.items():
        definition = inputs[name]
        if not isinstance(definition, dict):
            raise CompatibilityError(f"{name} definition must be a mapping")
        if definition.get("type") != input_type:
            raise CompatibilityError(f"{name} must have type {input_type}")
        actual_required = definition.get("required", False)
        if not isinstance(actual_required, bool) or actual_required is not required:
            raise CompatibilityError(f"{name}.required must be {str(required).lower()}")
    verify_idempotency_capability(source)
    verify_receiver_compatibility(source)
    return "exact two-input workflow_dispatch + idempotent receiver-compatible consumer"


def fetch_json(url: str, token: str | None = None) -> Any:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    debug(f"requesting {url} (authentication: {'configured' if token else 'not configured'})")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        status = f"HTTP {exc.code}: " if isinstance(exc, urllib.error.HTTPError) else ""
        safe_reason = str(getattr(exc, "reason", exc))
        safe_reason = re.sub(r"gh[pousr]_[A-Za-z0-9_]+", "[redacted-token]", safe_reason)
        safe_reason = re.sub(
            r"(?i)(authorization|token|secret|password)[:=][^\s,]+", r"\1=[redacted]", safe_reason
        )
        raise CompatibilityError(f"GitHub evidence is unavailable ({url}): {status}{safe_reason}") from exc


def fetch_content(repository: str, path: str, ref: str, token: str | None = None) -> bytes:
    quoted_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
    url = f"https://api.github.com/repos/{repository}/contents/{quoted_path}?ref={urllib.parse.quote(ref, safe='')}"
    payload = fetch_json(url, token)
    try:
        # GitHub's Contents API wraps Base64 content across multiple lines.
        encoded_content = "".join(payload["content"].split())
        content = base64.b64decode(encoded_content, validate=True)
        debug(f"received {len(content)} decoded bytes for {repository}/{path}@{ref}")
        return content
    except (KeyError, TypeError, ValueError) as exc:
        raise CompatibilityError("GitHub returned invalid file content") from exc


def fetch_workflow(repository: str, path: str, ref: str, token: str | None = None) -> str:
    try:
        return fetch_content(repository, path, ref, token).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CompatibilityError("GitHub returned non-UTF-8 workflow content") from exc


def fetch_ref_commit(repository: str, ref: str, token: str | None = None) -> str:
    url = f"https://api.github.com/repos/{repository}/commits/{urllib.parse.quote(ref, safe='')}"
    payload = fetch_json(url, token)
    commit = payload.get("sha") if isinstance(payload, dict) else None
    if not isinstance(commit, str) or SHA_RE.fullmatch(commit) is None:
        raise CompatibilityError("GitHub returned an invalid commit identity")
    return commit


def verify_receiver_at_ref(receiver_ref: str, token: str | None) -> None:
    receiver_commit = fetch_ref_commit("Young-Consultations/.github", receiver_ref, token)
    source = fetch_workflow(
        "Young-Consultations/.github",
        ".github/workflows/codex-result-receiver.yml",
        receiver_ref,
        token,
    )
    action_ref = verify_receiver_interface(source)
    action_commit = fetch_ref_commit("Young-Consultations/.github", action_ref, token)
    if action_commit != receiver_commit:
        raise CompatibilityError("result receiver workflow and action bundle resolve to different commits")
    action_source = fetch_workflow(
        "Young-Consultations/.github",
        "actions/codex-result-receiver/action.yml",
        action_ref,
        token,
    )
    verify_receiver_action(action_source)
    receiver_script = fetch_workflow(
        "Young-Consultations/.github",
        "scripts/codex_result_receiver.py",
        action_ref,
        token,
    )
    policy_raw = fetch_content(
        "Young-Consultations/.github",
        "config/codex-result-trust.json",
        action_ref,
        token,
    )
    verify_receiver_bundle_policy(receiver_script, policy_raw)
    fetch_content(
        "Young-Consultations/.github",
        "contracts/execution-result.schema.json",
        action_ref,
        token,
    )


def verify_conformance_pin(
    repository: str,
    ref: str,
    workflow_path: str,
    evidence: dict[str, Any],
    token: str | None,
) -> str:
    """Verify non-recursive evidence bindings at an immutable adapter ref."""
    raw = fetch_content(repository, CONFORMANCE_PIN_PATH, ref, token)
    try:
        pin = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, CompatibilityError) as exc:
        raise CompatibilityError("conformance pin is not valid JSON") from exc
    if not isinstance(pin, dict) or set(pin) != CONFORMANCE_PIN_FIELDS:
        raise CompatibilityError("conformance pin has an invalid shape")
    compatibility_files = pin.get("compatibility_files")
    target_files = pin.get("target_files")
    def valid_identity(value: Any) -> bool:
        return isinstance(value, str) and GIT_BLOB_RE.fullmatch(value) is not None

    def valid_path(value: Any) -> bool:
        return isinstance(value, str) and FILE_PATH_RE.fullmatch(value) is not None
    valid = (
        pin.get("pin_format_version") == 2
        and pin.get("organization_repository") == "Young-Consultations/.github"
        and pin.get("compatibility_sha") == evidence["compatibility_sha"]
        and pin.get("fixture_set") == "TC-MVP-CI-001"
        and pin.get("fixture_version") == evidence["fixture_version"]
        and isinstance(compatibility_files, dict)
        and set(compatibility_files) == PINNED_COMPATIBILITY_FILES
        and all(valid_path(path) and valid_identity(identity) for path, identity in compatibility_files.items())
        and isinstance(target_files, dict)
        and workflow_path in target_files
        and "scripts/run_tc_mvp_ci_001.py" in target_files
        and all(valid_path(path) and valid_identity(identity) for path, identity in target_files.items())
        and CONFORMANCE_PIN_PATH not in target_files
        and evidence["report_path"] not in target_files
    )
    if not valid:
        raise CompatibilityError("conformance pin does not bind the required compatibility and target files")
    expected_revision = conformance_pin_revision(pin)
    supplied_revision = pin.get("adapter_revision")
    if (
        not isinstance(supplied_revision, str)
        or PIN_REVISION_RE.fullmatch(supplied_revision) is None
        or supplied_revision != expected_revision
    ):
        raise CompatibilityError("conformance pin revision does not match its canonical file binding")

    for path, expected in compatibility_files.items():
        control_plane = fetch_content(
            "Young-Consultations/.github", path, evidence["compatibility_sha"], token,
        )
        target_copy = fetch_content(repository, path, ref, token)
        local_path = ROOT / path
        if (
            git_blob_sha1(control_plane) != expected
            or git_blob_sha1(target_copy) != expected
            or not local_path.is_file()
            or git_blob_sha1(local_path.read_bytes()) != expected
        ):
            raise CompatibilityError(f"conformance compatibility file identity differs: {path}")
    for path, expected in target_files.items():
        if git_blob_sha1(fetch_content(repository, path, ref, token)) != expected:
            raise CompatibilityError(f"conformance target file identity differs: {path}")
    return expected_revision


def verify_conformance_report(
    repository: str,
    ref: str,
    workflow_path: str,
    evidence: dict[str, Any],
    token: str | None,
) -> None:
    raw = fetch_content(repository, evidence["report_path"], ref, token)
    if hashlib.sha256(raw).hexdigest() != evidence["report_sha256"]:
        raise CompatibilityError("conformance report digest does not match the registry")
    try:
        report = json.loads(raw)
        fixture = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise CompatibilityError(f"conformance report cannot be loaded: {exc}") from exc
    adapter_revision = verify_conformance_pin(repository, ref, workflow_path, evidence, token)
    expected_scenarios = fixture.get("scenarios") if isinstance(fixture, dict) else None
    scenario_results = report.get("scenario_results") if isinstance(report, dict) else None
    observed_scenarios = [item.get("id") for item in scenario_results] if isinstance(scenario_results, list) and all(isinstance(item, dict) for item in scenario_results) else None
    all_pass = isinstance(scenario_results, list) and all(item.get("result") == "pass" for item in scenario_results if isinstance(item, dict))
    effect_traps = report.get("effect_traps") if isinstance(report, dict) else None
    zero_effects = isinstance(effect_traps, dict) and REQUIRED_ZERO_EFFECTS <= set(effect_traps) and all(
        isinstance(value, int) and not isinstance(value, bool) and value == 0
        for value in effect_traps.values()
    )
    valid = (
        report.get("report_version") == "1.0"
        and report.get("repository") == repository
        and report.get("adapter_revision") == adapter_revision
        and report.get("compatibility_sha") == evidence["compatibility_sha"]
        and report.get("fixture_set") == "TC-MVP-CI-001"
        and report.get("fixture_version") == evidence["fixture_version"]
        and report.get("activation_evidence_sufficient") is True
        and report.get("activation_requested") is False
        and report.get("production_readiness_claim") is False
        and report.get("failures") == []
        and observed_scenarios == expected_scenarios
        and all_pass
        and zero_effects
    )
    if not valid:
        raise CompatibilityError("conformance report does not prove the complete shared oracle with zero real effects")


def verify_registry(
    repositories: dict[str, dict[str, Any]], token: str | None,
    selected_repository: str | None = None, activation: dict[str, bool] | None = None,
) -> list[dict[str, str]]:
    if activation is None:
        activation = {repository: True for repository in repositories}
    report = []
    for repository, entry in repositories.items():
        if selected_repository is not None and repository != selected_repository:
            continue
        workflow_repository, path, ref = parse_workflow_ref(entry["workflow_ref"])
        enabled = activation[repository]
        row = {"repository": repository, "workflow": path, "ref": ref,
               "contract_version": entry["contract_version"], "draft_pr_only": str(entry["draft_pr_only"]).lower(),
               "transport_interface": "not evaluated", "result": "not-evaluated"}
        if not enabled and selected_repository is None:
            row["result"] = "not-evaluated: target disabled"
            debug(f"{repository}: {row['result']}")
            report.append(row)
            continue
        debug(f"checking {repository}: {path}@{ref}")
        try:
            if not IMMUTABLE_ADAPTER_TAG_RE.fullmatch(ref):
                raise CompatibilityError("workflow_ref must use a governed immutable codex-adapter-v* release tag")
            evidence = validate_conformance_record(repository, entry, required=True)
            if evidence is None:  # Defensive: required=True must never return None.
                raise CompatibilityError(f"{repository}: reviewed TC-MVP-CI-001 evidence is missing")
            commit = fetch_ref_commit(repository, ref, token)
            if commit != evidence["adapter_commit_sha"]:
                raise CompatibilityError("adapter tag does not resolve to the reviewed adapter commit")
            source = fetch_workflow(workflow_repository, path, ref, token)
            row["transport_interface"] = verify_interface(source)
            verify_receiver_at_ref(verify_receiver_compatibility(source), token)
            verify_conformance_report(repository, ref, path, evidence, token)
            row["result"] = "pass"
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
    parser.add_argument("--activation", type=Path, default=ACTIVATION)
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
            report = [{"repository": "fixture/canonical-target", "workflow": ".github/workflows/codex-execute.yml",
                       "ref": "fixture", "contract_version": CANONICAL_VERSION, "draft_pr_only": "true", "transport_interface": interface, "result": "pass"}]
        else:
            activation = load_activation(args.activation, repositories)
            token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
            if args.repository and args.repository not in repositories:
                raise CompatibilityError(f"{args.repository}: repository is not registered")
            report = verify_registry(repositories, token, args.repository, activation)
        write_outputs(report, args.report)
        failed = sum(row["result"] != "pass" for row in report)
        debug(f"wrote report to {args.report}; checked={len(report)}, nonpassing={failed}")
        return int(bool(failed))
    except (CompatibilityError, OSError) as exc:
        print(f"compatibility verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
