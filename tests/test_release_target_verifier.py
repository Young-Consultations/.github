from __future__ import annotations

import json
from pathlib import Path

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


@pytest.mark.parametrize(
    ("tag_published", "tag_commit_sha"),
    [
        (True, "4" * 40),
        (False, "4" * 40),
    ],
)
def test_local_receiver_fallback_requires_explicit_unpublished_candidate_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tag_published: bool,
    tag_commit_sha: str,
) -> None:
    def missing(receiver_ref: str, token: str | None) -> None:
        raise release_checker.checker.CompatibilityError(
            "GitHub evidence is unavailable (tag): HTTP 404: Not Found"
        )

    manifest = json.loads(
        release_checker.checker.RELEASE_MANIFEST.read_text(encoding="utf-8")
    )
    manifest["tag_published"] = tag_published
    manifest["tag_commit_sha"] = tag_commit_sha
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    (release_dir / "release-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    monkeypatch.setattr(release_checker, "ROOT", tmp_path)
    monkeypatch.setattr(release_checker, "_REMOTE_VERIFY_RECEIVER", missing)
    with pytest.raises(release_checker.checker.CompatibilityError, match="HTTP 404"):
        release_checker.verify_release_receiver_at_ref(manifest["tag"], "token")
