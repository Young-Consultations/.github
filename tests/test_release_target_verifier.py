from __future__ import annotations

import json

import pytest

from scripts import verify_release_target_workflows as release_checker


def _manifest_tag() -> str:
    return json.loads(release_checker.checker.RELEASE_MANIFEST.read_text(encoding="utf-8"))["tag"]


def test_remote_receiver_verification_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str | None]] = []

    def succeeds(receiver_ref: str, token: str | None) -> None:
        calls.append((receiver_ref, token))

    monkeypatch.setattr(release_checker, "_REMOTE_VERIFY_RECEIVER", succeeds)
    release_checker.verify_release_receiver_at_ref(_manifest_tag(), "token")
    assert calls == [(_manifest_tag(), "token")]


def test_exact_missing_manifest_tag_uses_reviewed_local_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(receiver_ref: str, token: str | None) -> None:
        raise release_checker.checker.CompatibilityError(
            "GitHub evidence is unavailable (tag): HTTP 422: Unprocessable Entity"
        )

    monkeypatch.setattr(release_checker, "_REMOTE_VERIFY_RECEIVER", missing)
    release_checker.verify_release_receiver_at_ref(_manifest_tag(), "token")


def test_missing_non_manifest_receiver_tag_still_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(receiver_ref: str, token: str | None) -> None:
        raise release_checker.checker.CompatibilityError(
            "GitHub evidence is unavailable (tag): HTTP 422: Unprocessable Entity"
        )

    monkeypatch.setattr(release_checker, "_REMOTE_VERIFY_RECEIVER", missing)
    with pytest.raises(release_checker.checker.CompatibilityError, match="HTTP 422"):
        release_checker.verify_release_receiver_at_ref("ai-sdlc-v9.9.9", "token")


def test_non_missing_manifest_receiver_failure_still_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def incompatible(receiver_ref: str, token: str | None) -> None:
        raise release_checker.checker.CompatibilityError("result receiver inputs are incompatible")

    monkeypatch.setattr(release_checker, "_REMOTE_VERIFY_RECEIVER", incompatible)
    with pytest.raises(release_checker.checker.CompatibilityError, match="inputs are incompatible"):
        release_checker.verify_release_receiver_at_ref(_manifest_tag(), "token")
