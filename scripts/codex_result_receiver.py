#!/usr/bin/env python3
"""Authenticated, idempotent execution-result/v2 receiver.

GitHub issue comments are the durable, source-owned delivery journal. Only
identity fields and digests are stored; the canonical payload is sent to the
source repository with ``repository_dispatch`` only after validation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts/execution-result.schema.json"
TRUST_POLICY = ROOT / "config/codex-result-trust.json"
ISSUE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100})#([1-9][0-9]*)$")
AUTHOR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*(?:\[bot\])?$")
ADMISSION = "<!-- ai-sdlc-admission:v2 "
RECEIPT = "<!-- ai-sdlc-result-receipt:v2 "
FORWARDED = "<!-- ai-sdlc-result-forwarded:v2 "


class ReceiverError(ValueError):
    def __init__(self, category: str, message: str, *, ambiguous: bool = False):
        super().__init__(message)
        self.category, self.ambiguous = category, ambiguous


class Journal(Protocol):
    def authenticate(self, repository: str) -> None: ...
    def comments(self, repository: str, issue: int) -> list[JournalComment]: ...
    def trusted_author(self, author: str, role: str) -> bool: ...
    def append(self, repository: str, issue: int, body: str) -> None: ...
    def forward(self, repository: str, projection: dict[str, Any]) -> None: ...


def load_trusted_authors(path: Path = TRUST_POLICY) -> dict[str, set[str]]:
    """Load the immutable control-plane journal-author policy.

    An empty list is the safe recovery default: the receiver remains deployed
    but rejects every journal marker until reviewed deployment identities are
    recorded in the compatibility release.
    """
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiverError("authentication", "result journal trust policy is unavailable") from exc
    expected_keys = {
        "policy_format_version", "trusted_admission_authors", "trusted_result_authors",
    }
    if not isinstance(policy, dict) or set(policy) != expected_keys:
        raise ReceiverError("authentication", "result journal trust policy has an invalid shape")
    if policy.get("policy_format_version") != 2:
        raise ReceiverError("authentication", "result journal trust policy has an unsupported version")
    roles: dict[str, set[str]] = {}
    for role, field in (("admission", "trusted_admission_authors"), ("result", "trusted_result_authors")):
        authors = policy.get(field)
        if not isinstance(authors, list):
            raise ReceiverError("authentication", "result journal trust policy has an invalid role allowlist")
        normalized: set[str] = set()
        for author in authors:
            if not isinstance(author, str) or not AUTHOR.fullmatch(author):
                raise ReceiverError("authentication", "result journal trust policy contains an invalid author")
            key = author.casefold()
            if key in normalized:
                raise ReceiverError("authentication", "result journal trust policy contains a duplicate author")
            normalized.add(key)
        if not normalized:
            raise ReceiverError("authentication", f"result journal trust policy denies all {role} authors")
        roles[role] = normalized
    if roles["admission"] & roles["result"]:
        raise ReceiverError("authentication", "result journal trust policy roles must be disjoint")
    return roles


def canonical_digest(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def visible_effect(result: dict[str, Any]) -> tuple[str, str]:
    """Return the stable visible-effect class and digest for retry comparison.

    ``draft-pr-created`` followed by ``duplicate-reused`` is the one approved
    non-identical result transition for a logical delivery. It is equivalent
    only when the managed draft and validation outcome are unchanged. Attempt
    metadata such as timestamps and workflow URL deliberately does not affect
    this digest.
    """
    status = result["execution_status"]
    effect_class = (
        "managed-draft"
        if status in {"draft-pr-created", "duplicate-reused"}
        else status
    )
    value = {
        "contract_version": result["contract_version"],
        "correlation_id": result["correlation_id"],
        "delivery_id": result["delivery_id"],
        "target_repository": result["target_repository"],
        "effect_class": effect_class,
        "branch_name": result["branch_name"],
        "pull_request_url": result["pull_request_url"],
        "validation_result": result["validation_result"],
        "test_result": result["test_result"],
        "failure_category": result["failure_category"],
    }
    return effect_class, canonical_digest(value)


def marker(prefix: str, value: dict[str, Any]) -> str:
    return prefix + json.dumps(value, separators=(",", ":"), sort_keys=True) + " -->"


@dataclass(frozen=True)
class JournalComment:
    body: str
    author: str


def parse_markers(comments: list[JournalComment], prefix: str, role: str, journal: Journal) -> list[dict[str, Any]]:
    found = []
    pattern = re.compile(re.escape(prefix) + r"(\{[^\n]*\}) -->")
    for comment in comments:
        if not journal.trusted_author(comment.author, role):
            continue
        for match in pattern.finditer(comment.body):
            try:
                value = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                found.append(value)
    return found


@dataclass(frozen=True)
class Receipt:
    accepted: bool
    delivery_id: str
    correlation_id: str
    execution_status: str
    failure_category: str
    diagnostic_summary: str
    duplicate: bool = False


def _equivalent_managed_draft_redelivery(
    prior: dict[str, Any], result: dict[str, Any], effect_class: str, effect_sha256: str
) -> bool:
    return (
        result["execution_status"] == "duplicate-reused"
        and effect_class == "managed-draft"
        and prior.get("effect_class") == "managed-draft"
        and prior.get("effect_sha256") == effect_sha256
    )


def receive(
    raw: str,
    source_issue: str,
    caller: str,
    journal: Journal,
    control_plane_release: str | None = None,
) -> Receipt:
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReceiverError("contract-validation", "execution_result is not valid JSON") from exc
    if not isinstance(result, dict):
        raise ReceiverError("contract-validation", "execution_result must be an object")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(result),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise ReceiverError("contract-validation", "execution_result failed canonical schema validation")
    match = ISSUE.fullmatch(source_issue)
    if not match:
        raise ReceiverError("contract-validation", "source_issue is malformed")
    source_repository, issue_number = match.group(1), int(match.group(2))
    if caller != result["target_repository"]:
        raise ReceiverError("authentication", "caller does not match target identity")
    journal.authenticate(source_repository)
    comments = journal.comments(source_repository, issue_number)
    bindings = [item for item in parse_markers(comments, ADMISSION, "admission", journal) if item.get("delivery_id") == result["delivery_id"]]
    expected = {
        "contract_version": result["contract_version"],
        "delivery_id": result["delivery_id"],
        "correlation_id": result["correlation_id"],
        "source_issue": source_issue,
        "target_repository": result["target_repository"],
    }
    unique_bindings = {json.dumps(item, separators=(",", ":"), sort_keys=True) for item in bindings}
    if len(unique_bindings) != 1 or any(bindings[0].get(key) != value for key, value in expected.items()):
        raise ReceiverError("authorization", "result does not match one admitted delivery binding")
    if control_plane_release and bindings[0].get("control_plane_release") != control_plane_release:
        raise ReceiverError("authorization", "result admission does not match the receiver release")

    digest = canonical_digest(result)
    effect_class, effect_sha256 = visible_effect(result)
    evidence = {
        **expected,
        "result_sha256": digest,
        "effect_class": effect_class,
        "effect_sha256": effect_sha256,
    }

    receipts = [item for item in parse_markers(comments, RECEIPT, "result", journal) if item.get("delivery_id") == result["delivery_id"]]
    equivalent_redelivery = False
    if receipts:
        if len(receipts) != 1:
            raise ReceiverError("unknown", "conflicting result exists for delivery", ambiguous=True)
        prior = receipts[0]
        if prior.get("result_sha256") == digest:
            pass
        elif _equivalent_managed_draft_redelivery(prior, result, effect_class, effect_sha256):
            equivalent_redelivery = True
        else:
            raise ReceiverError("unknown", "conflicting result exists for delivery", ambiguous=True)
    else:
        journal.append(
            source_repository,
            issue_number,
            marker(RECEIPT, {**evidence, "receiver_run_id": os.getenv("GITHUB_RUN_ID", "offline")}),
        )

    forwarded = [item for item in parse_markers(comments, FORWARDED, "result", journal) if item.get("delivery_id") == result["delivery_id"]]
    if forwarded:
        if len(forwarded) != 1:
            raise ReceiverError("unknown", "conflicting forwarded state exists for delivery", ambiguous=True)
        prior_forwarded = forwarded[0]
        if prior_forwarded.get("result_sha256") == digest or (
            equivalent_redelivery
            and prior_forwarded.get("effect_class") == effect_class
            and prior_forwarded.get("effect_sha256") == effect_sha256
        ):
            return Receipt(True, result["delivery_id"], result["correlation_id"], result["execution_status"], result["failure_category"], "Equivalent result already forwarded; no projection repeated.", True)
        raise ReceiverError("unknown", "conflicting forwarded state exists for delivery", ambiguous=True)

    journal.forward(source_repository, {"source_issue": source_issue, "execution_result": result})
    journal.append(source_repository, issue_number, marker(FORWARDED, evidence))
    return Receipt(True, result["delivery_id"], result["correlation_id"], result["execution_status"], result["failure_category"], "Validated result durably recorded and forwarded.")


class GitHubJournal:
    def __init__(self, trust_policy: Path = TRUST_POLICY) -> None:
        self._trusted_authors_by_role = load_trusted_authors(trust_policy)

    def _api(self, *args: str, input_value: dict[str, Any] | None = None) -> Any:
        cmd = ["gh", "api", *args]
        completed = subprocess.run(cmd, input=json.dumps(input_value) if input_value else None, text=True, capture_output=True, check=True)
        return json.loads(completed.stdout) if completed.stdout.strip() else None

    def authenticate(self, repository: str) -> None:
        data = self._api(f"repos/{repository}")
        if not isinstance(data, dict) or data.get("full_name") != repository:
            raise ReceiverError("authentication", "result credential is not authorized for source repository")

    def comments(self, repository: str, issue: int) -> list[JournalComment]:
        pages = self._api(
            "--paginate", "--slurp",
            f"repos/{repository}/issues/{issue}/comments?per_page=100",
        )
        if not isinstance(pages, list):
            raise ReceiverError("dependency", "issue comment response is not a list")
        data = (
            [item for page in pages for item in page]
            if all(isinstance(page, list) for page in pages)
            else pages
        )
        return [JournalComment(str(item.get("body", "")), str(item.get("user", {}).get("login", ""))) for item in data if isinstance(item, dict)]

    def trusted_author(self, author: str, role: str) -> bool:
        return author.casefold() in self._trusted_authors_by_role.get(role, set())

    def append(self, repository: str, issue: int, body: str) -> None:
        self._api(f"repos/{repository}/issues/{issue}/comments", "--method", "POST", "-f", f"body={body}")

    def forward(self, repository: str, projection: dict[str, Any]) -> None:
        self._api(f"repos/{repository}/dispatches", "--method", "POST", "--input", "-", input_value={"event_type": "ai-sdlc-execution-result-v2", "client_payload": projection})


def _output(name: str, value: Any) -> None:
    rendered = str(value).lower() if isinstance(value, bool) else str(value)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
        stream.write(f"{name}={rendered}\n")


def main() -> int:
    try:
        receipt = receive(
            os.environ.get("EXECUTION_RESULT", ""),
            os.environ.get("SOURCE_ISSUE", ""),
            os.environ.get("CALLER_REPOSITORY", ""),
            GitHubJournal(),
            os.environ.get("CONTROL_PLANE_RELEASE") or None,
        )
    except (ReceiverError, OSError, subprocess.CalledProcessError) as exc:
        category = exc.category if isinstance(exc, ReceiverError) else "dependency"
        ambiguous = isinstance(exc, ReceiverError) and exc.ambiguous
        values = {"accepted": False, "delivery_id": "", "correlation_id": "", "execution_status": "ambiguous-rejected" if ambiguous else "rejected", "failure_category": category, "diagnostic_summary": str(exc)[:300]}
        for key, value in values.items(): _output(key, value)
        print(f"::error::{values['diagnostic_summary']}", file=sys.stderr)
        return 1
    for key in Receipt.__dataclass_fields__:
        if key != "duplicate": _output(key, getattr(receipt, key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
