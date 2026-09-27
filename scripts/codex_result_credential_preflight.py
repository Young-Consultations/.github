#!/usr/bin/env python3
"""Fail-closed preflight for the result-delivery credential.

This check runs before a cost-bearing execution provider. It uses bounded
credential probes to verify the actual issue-comment author, issue write access,
cleanup access, and repository-dispatch access required by the receiver.
"""
from __future__ import annotations

import os
import subprocess
import sys

try:
    from codex_result_receiver import GitHubJournal, ISSUE, ReceiverError
except ModuleNotFoundError:  # Imported as scripts.codex_result_credential_preflight in tests.
    from scripts.codex_result_receiver import GitHubJournal, ISSUE, ReceiverError


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
        journal.probe_forward(repository)
    except (ReceiverError, OSError, subprocess.CalledProcessError) as exc:
        print(f"::error::{str(exc)[:300]}", file=sys.stderr)
        return 1
    print("Result credential identity and required source write capabilities verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
