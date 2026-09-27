#!/usr/bin/env python3
"""Fail-closed preflight for the result-delivery credential.

This check is intended to run before a cost-bearing execution provider. It
verifies that the configured credential resolves to an immutable trusted result
journal author and can authenticate to the source repository. It performs no
source mutation.
"""
from __future__ import annotations

import os
import re
import sys

try:
    from codex_result_receiver import GitHubJournal, ReceiverError
except ModuleNotFoundError:  # Imported as scripts.codex_result_credential_preflight in tests.
    from scripts.codex_result_receiver import GitHubJournal, ReceiverError

REPOSITORY = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}$"
)


def main() -> int:
    repository = os.environ.get("SOURCE_REPOSITORY", "")
    if REPOSITORY.fullmatch(repository) is None:
        print("::error::source repository is malformed", file=sys.stderr)
        return 1
    try:
        GitHubJournal().authenticate(repository)
    except (ReceiverError, OSError) as exc:
        print(f"::error::{str(exc)[:300]}", file=sys.stderr)
        return 1
    print("Result credential identity and source repository access verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
