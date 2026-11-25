"""Deny-only rollback metadata for v5; never execution authority."""
from __future__ import annotations

import json
from typing import Any

LEGACY_TAG = "ai-sdlc-v4.0.0"
LEGACY_SHA = "6e51f058bf828b0732cb1b773ba1835acaa1d5cd"
LEGACY_PREDECESSOR = {
    "release_version": "2.4.4",
    "commit_sha": "adb57508762168b3410f52e8a7b0151078c6e9b9",
}
STATE = "no-reviewed-safe-rollback"


def deny_policy() -> dict[str, Any]:
    return {"state": STATE, "candidate": None, "real_resume_authorized": False}


def strict_json(raw: str) -> Any:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate release JSON key")
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError("nonfinite release JSON value")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def valid_policy(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"state", "candidate", "real_resume_authorized"}
        and value["state"] == STATE
        and value["candidate"] is None
        and value["real_resume_authorized"] is False
    )


def legacy_manifest(manifest: dict) -> bool:
    return (
        manifest.get("release_version") == "4.0.0"
        and manifest.get("tag") == LEGACY_TAG
        and manifest.get("tag_published") is True
        and manifest.get("tag_commit_sha") == LEGACY_SHA
        and manifest.get("previous_known_good") == LEGACY_PREDECESSOR
        and "rollback_policy" not in manifest
    )


def manifest_errors(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict):
        return ["rollback: invalid manifest"]
    if legacy_manifest(manifest):
        return []
    if manifest.get("release_version") != "5.0.0" or manifest.get("tag") != "ai-sdlc-v5.0.0":
        return ["rollback: unsupported release identity (only attested v4 and v5 supported)"]
    if "previous_known_good" in manifest:
        return ["rollback: legacy predecessor field forbidden for v5"]
    if not valid_policy(manifest.get("rollback_policy")):
        return ["rollback: v5 requires the exact deny-only policy"]
    return []


def runtime_errors(manifest: Any, runtime: Any) -> list[str]:
    errors = manifest_errors(manifest)
    if errors:
        return errors
    if not isinstance(runtime, dict) or not isinstance(runtime.get("control_plane"), dict):
        return ["rollback: invalid runtime record"]
    control = runtime["control_plane"]
    if any(control.get(k) != manifest.get(k) for k in (
        "release_version", "tag", "tag_published", "tag_commit_sha"
    )) or runtime.get("release_state") != (
        "published" if manifest.get("tag_published") is True else "candidate"
    ):
        return ["rollback: runtime release identity differs from manifest"]
    if "previous_known_good" in runtime or "previous_known_good" in control or "rollback_policy" in control:
        return ["rollback: unexpected rollback fields in runtime"]
    if legacy_manifest(manifest):
        return ["rollback: legacy runtime must remain unchanged"] if "rollback_policy" in runtime else []
    if not valid_policy(runtime.get("rollback_policy")) or runtime["rollback_policy"] != manifest["rollback_policy"]:
        return ["rollback: runtime policy differs from manifest"]
    return []


def recovery_denial() -> dict[str, Any]:
    return {
        "status": "FAIL",
        "rollback_policy": deny_policy(),
        "failures": ["rollback: no reviewed safe rollback available; REAL resume denied"],
        "next_action": "hold new implementation dispatch; review and verify a recovery release; obtain separate human authorization",
    }
