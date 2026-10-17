#!/usr/bin/env python3
"""Fail-closed preflight for the result-delivery credential.

This check runs before a cost-bearing execution provider. It uses bounded
credential probes to verify the actual issue-comment author, issue write access,
cleanup access, and repository-dispatch access required by the receiver.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

try:
    from codex_result_receiver import (
        ADMISSION, FORWARDED, RECEIPT, GitHubJournal, ISSUE, ReceiverError, parse_markers,
    )
except ModuleNotFoundError:  # Imported as scripts.codex_result_credential_preflight in tests.
    from scripts.codex_result_receiver import (
        ADMISSION, FORWARDED, RECEIPT, GitHubJournal, ISSUE, ReceiverError, parse_markers,
    )



_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_BINDING_FIELDS = ("contract_version", "delivery_id", "correlation_id", "source_issue", "target_repository")


def check_prior_result(journal, source_issue: str, repository: str, issue_number: int,
                       raw_input: str) -> str:
    """Read trusted durable result state before a model call.

    A managed-draft receipt is allowed through for ownership reconciliation,
    not permission for a second executor call. Target consumers MUST stop
    before Codex if no matching owned managed draft is found.
    """
    if not raw_input:
        # Legacy callers remain compatible, but this is NOT a readiness proof.
        return "not-checked"
    try:
        payload = json.loads(raw_input)
    except (ValueError, TypeError) as exc:
        raise ReceiverError("contract-validation", "execution input is malformed") from exc
    if not isinstance(payload, dict) or any(
        not isinstance(payload.get(field), str) or not payload[field]
        for field in _BINDING_FIELDS
    ):
        raise ReceiverError("contract-validation", "execution input binding is incomplete")
    expected = {field: payload[field] for field in _BINDING_FIELDS}
    if payload["source_issue"] != source_issue or payload["contract_version"] != "ai-sdlc-contract/v2":
        raise ReceiverError("authorization", "execution input does not match preflight source")

    comments = journal.comments(repository, issue_number)
    admissions = [
        item for item in parse_markers(comments, ADMISSION, "admission", journal)
        if item.get("delivery_id") == expected["delivery_id"]
    ]
    unique = {json.dumps(item, sort_keys=True, separators=(",", ":")) for item in admissions}
    if len(unique) != 1 or any(
        admissions[0].get(field) != value for field, value in expected.items()
    ):
        raise ReceiverError("authorization", "preflight delivery lacks unique trusted admission")

    receipts = [
        item for item in parse_markers(comments, RECEIPT, "result", journal)
        if item.get("delivery_id") == expected["delivery_id"]
    ]
    forwarded = [
        item for item in parse_markers(comments, FORWARDED, "result", journal)
        if item.get("delivery_id") == expected["delivery_id"]
    ]
    if not receipts:
        if forwarded:
            raise ReceiverError("unknown", "delivery has forwarding without a trusted receipt", ambiguous=True)
        return "none"
    if len(receipts) != 1 or len(forwarded) != 1:
        raise ReceiverError("unknown", "ambiguous terminal receipt state", ambiguous=True)
    receipt, sent = receipts[0], forwarded[0]
    for record in (receipt, sent):
        if any(record.get(field) != value for field, value in expected.items()):
            raise ReceiverError("authorization", "terminal evidence identity mismatch")
        if not all(isinstance(record.get(key), str) and _DIGEST.fullmatch(record[key])
                   for key in ("result_sha256", "effect_sha256")):
            raise ReceiverError("unknown", "terminal evidence digest is malformed", ambiguous=True)
    if any(receipt.get(key) != sent.get(key) for key in
           ("result_sha256", "effect_class", "effect_sha256")):
        raise ReceiverError("unknown", "terminal result forwarding is inconsistent", ambiguous=True)
    if receipt.get("effect_class") != "managed-draft":
        raise ReceiverError(
            "authorization",
            "delivery already has a terminal result; new authorization is required",
        )
    return "managed-draft"


def main() -> int:
    source_issue = os.environ.get("SOURCE_ISSUE", "")
    match = ISSUE.fullmatch(source_issue)
    if match is None:
        print("::error::source issue is malformed", file=sys.stderr)
        return 1
    repository, issue_number = match.group(1), int(match.group(2))
    try:
        journal = GitHubJournal()
        journal.authenticate(repository, issue_number)
        prior_effect = check_prior_result(
            journal, source_issue, repository, issue_number,
            os.environ.get("EXECUTION_INPUT_JSON", ""),
        )
        journal.probe_forward(repository)
        output_path = os.environ.get("GITHUB_OUTPUT")
        if output_path:
            with open(output_path, "a", encoding="utf-8") as output:
                output.write(f"prior_effect_class={prior_effect}\n")
    except (ReceiverError, OSError, subprocess.CalledProcessError) as exc:
        print(f"::error::{str(exc)[:300]}", file=sys.stderr)
        return 1
    print("Result credential identity and source access verified; delivery result state checked where bound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
