#!/usr/bin/env python3
"""Release-aware wrapper for registered target compatibility verification.

The normal verifier resolves immutable receiver refs from GitHub. During the narrow
release window where a reviewed target already pins the exact next manifest tag but
that tag has not yet been created, release verification must instead validate the
current reviewed control-plane checkout. All other missing or unavailable receiver
refs continue to fail closed.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts import verify_target_workflows as checker

ROOT = Path(__file__).resolve().parents[1]
_REMOTE_VERIFY_RECEIVER = checker.verify_receiver_at_ref


def _missing_ref_error(exc: checker.CompatibilityError) -> bool:
    message = str(exc)
    return "HTTP 404:" in message or "HTTP 422:" in message


def verify_release_receiver_at_ref(receiver_ref: str, token: str | None) -> None:
    try:
        _REMOTE_VERIFY_RECEIVER(receiver_ref, token)
        return
    except checker.CompatibilityError as exc:
        manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
        if receiver_ref != manifest.get("tag") or not _missing_ref_error(exc):
            raise

    workflow_path = ROOT / manifest["result_receiver_workflow"]
    action_path = ROOT / manifest["result_receiver_action"]
    trust_path = ROOT / manifest["result_trust_policy"]
    receiver_script_path = ROOT / "scripts/codex_result_receiver.py"
    schema_path = ROOT / "contracts/execution-result.schema.json"

    source = workflow_path.read_text(encoding="utf-8")
    action_ref = checker.verify_receiver_interface(source)
    if action_ref != receiver_ref:
        raise checker.CompatibilityError(
            "local release-candidate receiver does not self-pin the exact manifest tag"
        )
    checker.verify_receiver_action(action_path.read_text(encoding="utf-8"))
    checker.verify_receiver_bundle_policy(
        receiver_script_path.read_text(encoding="utf-8"),
        trust_path.read_bytes(),
    )
    if not schema_path.is_file():
        raise checker.CompatibilityError("local release-candidate result schema is missing")
    checker.debug(
        f"{receiver_ref}: remote tag is unused; verified exact manifest receiver candidate from current checkout"
    )


def main(argv: list[str] | None = None) -> int:
    checker.verify_receiver_at_ref = verify_release_receiver_at_ref
    return checker.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
