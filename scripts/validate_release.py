#!/usr/bin/env python3
"""Validate that one release manifest describes the complete control plane."""
from __future__ import annotations

import argparse
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
IMMUTABLE_ADAPTER_TAG = re.compile(
    r"codex-adapter-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
)
SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
AUTHOR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*(?:\[bot\])?$")
REPORT_PATH = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+\.json$")
CONFORMANCE_FIELDS = {
    "fixture_set", "fixture_version", "compatibility_sha", "adapter_ref",
    "adapter_commit_sha", "report_path", "report_sha256", "status",
    "activation_evidence_sufficient",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe_manifest_json_path(root: Path, value: object, field: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or REPORT_PATH.fullmatch(value) is None:
        errors.append(f"{field} must be a safe repository-relative JSON path")
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{field} must stay within the repository")
        return None
    return candidate


def conformance_errors(repository: str, entry: dict, fixture_version: object) -> list[str]:
    evidence = entry.get("conformance")
    if not isinstance(evidence, dict) or set(evidence) != CONFORMANCE_FIELDS:
        return [f"{repository}: reviewed conformance evidence is missing or malformed"]
    workflow_ref = str(entry.get("workflow_ref", ""))
    adapter_ref = workflow_ref.rsplit("@", 1)[-1] if "@" in workflow_ref else ""
    valid = (
        evidence.get("fixture_set") == "TC-MVP-CI-001"
        and evidence.get("fixture_version") == fixture_version
        and evidence.get("adapter_ref") == adapter_ref
        and isinstance(evidence.get("compatibility_sha"), str)
        and SHA.fullmatch(evidence["compatibility_sha"]) is not None
        and isinstance(evidence.get("adapter_commit_sha"), str)
        and SHA.fullmatch(evidence["adapter_commit_sha"]) is not None
        and isinstance(evidence.get("report_path"), str)
        and REPORT_PATH.fullmatch(evidence["report_path"]) is not None
        and isinstance(evidence.get("report_sha256"), str)
        and DIGEST.fullmatch(evidence["report_sha256"]) is not None
        and evidence.get("status") == "pass"
        and evidence.get("activation_evidence_sufficient") is True
    )
    return [] if valid else [f"{repository}: reviewed conformance evidence is invalid"]


def validate(root: Path = ROOT, *, require_publishable: bool = False) -> list[str]:
    errors: list[str] = []
    manifest = load_json(root / MANIFEST.relative_to(ROOT))
    version = manifest.get("release_version", "")
    if not SEMVER.fullmatch(version):
        errors.append("release_version must be semantic versioning")
    if manifest.get("tag") != f"ai-sdlc-v{version}":
        errors.append("tag must map exactly to release_version")
    if not isinstance(manifest.get("tag_published"), bool):
        errors.append("tag_published must explicitly record publication state")
    if require_publishable and manifest.get("tag_published") is not True:
        errors.append("publishable release must declare tag_published true")
    tag_commit_sha = manifest.get("tag_commit_sha")
    if manifest.get("tag_published") is True and (
        not isinstance(tag_commit_sha, str) or SHA.fullmatch(tag_commit_sha) is None
    ):
        errors.append("published release must record the immutable tag commit SHA")
    if manifest.get("tag_published") is False and tag_commit_sha is not None:
        errors.append("candidate release must not claim a tag commit SHA")
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
        if "conformance" not in entry:
            errors.append(f"{repository}: conformance evidence field is missing")
        if entry.get("conformance") is not None or require_publishable:
            errors.extend(conformance_errors(repository, entry, manifest.get("fixture_version")))
        if require_publishable:
            ref = str(entry.get("workflow_ref", "")).rsplit("@", 1)[-1]
            if IMMUTABLE_ADAPTER_TAG.fullmatch(ref) is None:
                errors.append(f"{repository}: publishable release requires an immutable codex-adapter-v* tag")
    activation = load_json(root / "config/codex-activation.json")
    targets = activation.get("targets")
    if activation.get("activation_format_version") != 1 or not isinstance(targets, dict):
        errors.append("activation configuration has an unsupported format")
    elif set(targets) != set(registry) or any(not isinstance(value, bool) for value in targets.values()):
        errors.append("activation configuration must contain one boolean per capability")

    runtime_path = safe_manifest_json_path(
        root, manifest.get("current_runtime"), "current_runtime", errors
    )
    credential_roles_path = safe_manifest_json_path(
        root, manifest.get("credential_role_manifest"), "credential_role_manifest", errors
    )
    if runtime_path is None or not runtime_path.is_file():
        errors.append("generated current runtime record must exist")
    else:
        runtime = load_json(runtime_path)
        control_plane = runtime.get("control_plane", {}) if isinstance(runtime, dict) else {}
        if (
            runtime.get("runtime_record_format_version") != 1
            or control_plane.get("tag") != manifest.get("tag")
            or control_plane.get("tag_published") != manifest.get("tag_published")
            or control_plane.get("tag_commit_sha") != manifest.get("tag_commit_sha")
        ):
            errors.append("generated current runtime record is inconsistent with the manifest")
    if credential_roles_path is None or not credential_roles_path.is_file():
        errors.append("credential role manifest must exist")
    else:
        roles = load_json(credential_roles_path)
        if (
            roles.get("credential_role_format_version") != 1
            or not isinstance(roles.get("repositories"), dict)
            or not roles["repositories"]
        ):
            errors.append("credential role manifest is invalid")

    router = manifest.get("router_workflow")
    router_action = manifest.get("router_action")
    if not isinstance(router, str) or not (root / router).is_file():
        errors.append("release router workflow must exist")
    elif not isinstance(router_action, str) or not (root / router_action).is_file():
        errors.append("release router action must exist")
    else:
        router_source = (root / router).read_text(encoding="utf-8")
        expected_router_action = (
            "Young-Consultations/.github/actions/codex-router@"
            + str(manifest.get("tag", ""))
        )
        if router_source.count(expected_router_action) != 1:
            errors.append("release router must self-pin its action bundle to the release tag")
        if "github.workflow_sha" in router_source or "actions/checkout@" in router_source:
            errors.append("release router workflow must not resolve policy through caller context")

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
    else:
        receiver_source = (root / receiver).read_text(encoding="utf-8")
        expected_action = (
            "Young-Consultations/.github/actions/codex-result-receiver@"
            + str(manifest.get("tag", ""))
        )
        if receiver_source.count(expected_action) != 1:
            errors.append("release result receiver must self-pin its action bundle to the release tag")
        if "actions/checkout@" in receiver_source:
            errors.append("release result receiver must not checkout caller-controlled policy content")
    receiver_action = manifest.get("result_receiver_action")
    if not isinstance(receiver_action, str) or not (root / receiver_action).is_file():
        errors.append("release result receiver action must exist")
    trust_policy_path = manifest.get("result_trust_policy")
    if not isinstance(trust_policy_path, str) or not (root / trust_policy_path).is_file():
        errors.append("release result trust policy must exist")
    else:
        try:
            trust_policy = load_json(root / trust_policy_path)
        except (OSError, json.JSONDecodeError):
            errors.append("release result trust policy must be valid JSON")
        else:
            admission_authors = trust_policy.get("trusted_admission_authors") if isinstance(trust_policy, dict) else None
            result_authors = trust_policy.get("trusted_result_authors") if isinstance(trust_policy, dict) else None
            author_lists = (admission_authors, result_authors)
            valid_authors = (
                isinstance(trust_policy, dict)
                and set(trust_policy) == {"policy_format_version", "trusted_admission_authors", "trusted_result_authors"}
                and trust_policy.get("policy_format_version") == 2
                and all(isinstance(authors, list) for authors in author_lists)
                and all(isinstance(author, str) and AUTHOR.fullmatch(author) for authors in author_lists for author in authors)
                and all(len({author.casefold() for author in authors}) == len(authors) for authors in author_lists)
                and not ({author.casefold() for author in admission_authors} & {author.casefold() for author in result_authors})
            )
            if not valid_authors:
                errors.append("release result trust policy is invalid")
            elif require_publishable and not all(author_lists):
                errors.append("publishable release must name trusted authors for every journal role")

    paths = [*root.glob(".github/workflows/*.yml"), *root.glob("docs/*.md"), root / "README.md"]
    for path in paths:
        if match := MUTABLE_REUSABLE.search(path.read_text(encoding="utf-8")):
            errors.append(f"{path.relative_to(root)}: mutable organization workflow ref @{match.group(1)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-publishable", action="store_true",
        help="require immutable adapter tags, reviewed conformance, deployment trust authors, and a publishable tag state",
    )
    args = parser.parse_args(argv)
    errors = validate(require_publishable=args.require_publishable)
    if errors:
        print("release validation failed:\n- " + "\n- ".join(errors), file=sys.stderr)
        return 1
    print("release manifest is coherent and organization workflow references are immutable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
