#!/usr/bin/env python3
"""Generate the single machine-readable current runtime composition."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "release/current-runtime.json"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def render() -> str:
    manifest = load("release/release-manifest.json")
    registry = load(manifest["registry"])["repositories"]
    activation_path = ROOT / "config/codex-activation.json"
    activation = json.loads(activation_path.read_text(encoding="utf-8"))["targets"]
    credential_path = manifest["credential_role_manifest"]
    credentials = load(credential_path)
    document = {
        "runtime_record_format_version": 1,
        "release_state": "published" if manifest["tag_published"] else "candidate",
        "control_plane": {
            "release_version": manifest["release_version"],
            "tag": manifest["tag"],
            "tag_published": manifest["tag_published"],
            "router_workflow": manifest["router_workflow"],
            "router_action": manifest["router_action"],
            "result_receiver_workflow": manifest["result_receiver_workflow"],
            "result_receiver_action": manifest["result_receiver_action"],
        },
        "activation": {
            "source": "Young-Consultations/.github@main:config/codex-activation.json",
            "sha256": hashlib.sha256(activation_path.read_bytes()).hexdigest(),
            "enabled_targets": sorted(name for name, enabled in activation.items() if enabled),
        },
        "targets": {
            name: {
                "enabled": activation[name],
                "workflow_ref": entry["workflow_ref"],
                "contract_version": entry["contract_version"],
                "draft_pr_only": entry["draft_pr_only"],
            }
            for name, entry in sorted(registry.items())
        },
        "credential_role_manifest": {
            "path": credential_path,
            "sha256": hashlib.sha256(
                (ROOT / credential_path).read_bytes()
            ).hexdigest(),
            "scope": credentials["scope"],
        },
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("release/current-runtime.json is stale")
            return 1
        print("current runtime record is synchronized")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    print(OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
