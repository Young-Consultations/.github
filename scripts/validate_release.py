#!/usr/bin/env python3
"""Validate that one release manifest describes the complete control plane."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release/release-manifest.json"
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
MUTABLE_REUSABLE = re.compile(
    r"Young-Consultations/\.github/\.github/workflows/[^\s@]+@(main|master)\b"
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    manifest = load_json(root / MANIFEST.relative_to(ROOT))
    version = manifest.get("release_version", "")
    if not SEMVER.fullmatch(version):
        errors.append("release_version must be semantic versioning")
    if manifest.get("tag") != f"ai-sdlc-v{version}":
        errors.append("tag must map exactly to release_version")
    if not isinstance(manifest.get("tag_published"), bool):
        errors.append("tag_published must explicitly record publication state")
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    package_match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    if not package_match or package_match.group(1) != manifest.get("contract_package_version"):
        errors.append("package version does not match release manifest")

    contract_version = (root / "contracts/contract-version.txt").read_text(encoding="utf-8").strip()
    if contract_version != manifest.get("contract_payload_version") or contract_version != manifest.get("schema_version"):
        errors.append("contract and schema versions do not match release manifest")

    registry_document = load_json(root / manifest["registry"])
    if registry_document.get("registry_format_version") != manifest.get("registry_format_version"):
        errors.append("registry format version does not match release manifest")
    registry = registry_document["repositories"]
    if sorted(registry) != manifest.get("supported_targets"):
        errors.append("release targets do not exactly match the registry allowlist")
    for repository, entry in registry.items():
        if "enabled" in entry:
            errors.append(f"{repository}: mutable activation must not be embedded in capabilities")
        if entry.get("contract_version") != contract_version:
            errors.append(f"{repository}: contract version drift")
        if entry.get("draft_pr_only") is not True:
            errors.append(f"{repository}: draft-only execution is required")
    activation = load_json(root / "config/codex-activation.json")
    targets = activation.get("targets")
    if activation.get("activation_format_version") != 1 or not isinstance(targets, dict):
        errors.append("activation configuration has an unsupported format")
    elif set(targets) != set(registry) or any(not isinstance(value, bool) for value in targets.values()):
        errors.append("activation configuration must contain one boolean per capability")

    previous = manifest.get("previous_known_good", {})
    if not re.fullmatch(r"[0-9a-f]{40}", previous.get("commit_sha", "")):
        errors.append("previous known-good release must have a full commit SHA")

    fixture_path = manifest.get("fixture_manifest")
    if not isinstance(fixture_path, str) or not (root / fixture_path).is_file():
        errors.append("release fixture manifest must exist")
    else:
        fixture = load_json(root / fixture_path)
        if fixture.get("fixture_version") != manifest.get("fixture_version"):
            errors.append("fixture version does not match release manifest")
    receiver = manifest.get("result_receiver_workflow")
    if not isinstance(receiver, str) or not (root / receiver).is_file():
        errors.append("release result receiver workflow must exist")

    paths = [*root.glob(".github/workflows/*.yml"), *root.glob("docs/*.md"), root / "README.md"]
    for path in paths:
        if match := MUTABLE_REUSABLE.search(path.read_text(encoding="utf-8")):
            errors.append(f"{path.relative_to(root)}: mutable organization workflow ref @{match.group(1)}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("release validation failed:\n- " + "\n- ".join(errors), file=sys.stderr)
        return 1
    print("release manifest is coherent and organization workflow references are immutable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
