#!/usr/bin/env python3
"""Fail-closed target adapter for the Young-Consultations/.github repository.

The pure ``run_adapter`` entry point is intentionally dependency-injected so
TC-MVP-CI-001 can exercise every transition without Codex or GitHub effects.
The command-line adapter uses ``gh`` only after admission and reconciliation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
TARGET = "Young-Consultations/.github"
MARKER = "ai-sdlc-delivery-id"
ALLOWED_TYPES = {"ci-cd", "documentation", "repository-maintenance", "testing"}
SAFE_ENV = {"PATH", "HOME", "LANG", "LC_ALL", "CI", "GITHUB_ACTIONS"}


class AdapterError(Exception):
    def __init__(self, category: str, message: str, status: str = "rejected"):
        self.category, self.safe_message, self.status = category, message[:500], status
        super().__init__(self.safe_message)


class Effects(Protocol):
    def discover(self, branch: str, delivery_id: str) -> list[dict[str, Any]]: ...
    def codex(self, instructions: str) -> None: ...
    def validate_candidate(self) -> tuple[bool, str]: ...
    def publish(self, branch: str, delivery_id: str, digest: str) -> str: ...


@dataclass
class Outcome:
    result: dict[str, Any]
    source_issue: str | None


def canonical_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _result(payload: dict[str, Any], started: str, status: str, category: str,
            message: str | None, *, branch: str | None = None, pr: str | None = None,
            validation: str = "not-run", tests: str = "not-run") -> dict[str, Any]:
    result = {
        "contract_version": "ai-sdlc-contract/v2",
        "correlation_id": payload.get("correlation_id", "untrusted"),
        "delivery_id": payload.get("delivery_id", "untrusted"),
        "execution_status": status,
        "target_repository": payload.get("target_repository", TARGET),
        "branch_name": branch,
        "pull_request_url": pr,
        "workflow_url": os.getenv("GITHUB_SERVER_URL", "https://github.com") + "/" +
            os.getenv("GITHUB_REPOSITORY", TARGET) + "/actions/runs/" + os.getenv("GITHUB_RUN_ID", "1"),
        "validation_result": validation,
        "test_result": tests,
        "failure_category": category,
        "failure_message": message,
        "started_at": started,
        "completed_at": _now(),
    }
    schema = json.loads((ROOT / "contracts/execution-result.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(result)
    return result


def admit(raw: str, transport_group: str, caller: str, trusted_callers: set[str],
          registry: dict[str, Any]) -> dict[str, Any]:
    if caller not in trusted_callers:
        raise AdapterError("authentication", "Caller is not authorized for target execution")
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        raise AdapterError("contract-validation", "Execution input is not valid JSON")
    if not isinstance(payload, dict):
        raise AdapterError("contract-validation", "Execution input must be an object")
    schema = json.loads((ROOT / "contracts/execution-input.schema.json").read_text())
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload))
    if errors:
        raise AdapterError("contract-validation", "Execution input does not conform to execution-input/v2")
    if payload["concurrency_group"] != transport_group or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,254}", transport_group):
        raise AdapterError("contract-validation", "Transport concurrency group is invalid or does not match payload")
    entry = registry.get("repositories", {}).get(TARGET)
    if not entry or not entry.get("enabled"):
        raise AdapterError("repository-routing", "Target is not enabled in the registry")
    if payload["target_repository"] != TARGET:
        raise AdapterError("repository-routing", "Execution input targets a different repository")
    if entry.get("contract_version") != payload["contract_version"]:
        raise AdapterError("contract-validation", "Target does not support this contract version")
    if payload["task_type"] not in ALLOWED_TYPES or payload["task_type"] not in entry.get("allowed_task_types", []):
        raise AdapterError("authorization", "Task type is not authorized for this target")
    if payload["execution_mode"] not in {"verify", "implement"} or payload["executor"] != "codex" or payload["draft_pr_only"] is not True:
        raise AdapterError("authorization", "Execution policy is not authorized")
    expected = f"codex/{payload['delivery_id'].lower()}"
    if payload["requested_branch"] not in (None, expected):
        raise AdapterError("authorization", "Requested branch contradicts delivery ownership")
    return payload


def run_adapter(raw: str, transport_group: str, caller: str, trusted_callers: set[str],
                registry: dict[str, Any], effects: Effects) -> Outcome:
    started, parsed = _now(), {}
    try:
        try:
            candidate = json.loads(raw)
            if isinstance(candidate, dict):
                parsed = candidate
        except Exception:
            pass
        payload = admit(raw, transport_group, caller, trusted_callers, registry)
        digest = canonical_digest(payload)
        branch = f"codex/{payload['delivery_id'].lower()}"
        owned = effects.discover(branch, payload["delivery_id"])
        if any(x.get("digest") != digest for x in owned):
            raise AdapterError("authorization", "Delivery ID is already bound to a different payload", "ambiguous-rejected")
        if len(owned) > 1 or any(not x.get("draft") or x.get("state") != "OPEN" for x in owned):
            raise AdapterError("publication", "Delivery ownership is ambiguous", "ambiguous-rejected")
        if len(owned) == 1:
            pr = owned[0]["url"]
            return Outcome(_result(payload, started, "duplicate-reused", "none", None,
                                   branch=branch, pr=pr, validation="passed", tests="passed"), payload["source_issue"])
        if payload["execution_mode"] == "verify":
            return Outcome(_result(payload, started, "verified", "none", None,
                                   validation="passed", tests="passed"), payload["source_issue"])
        effects.codex(payload["instructions"])
        valid, phase = effects.validate_candidate()
        if not valid:
            category = "tests" if phase == "tests" else "validation"
            raise AdapterError(category, "Candidate did not pass repository policy", "failed")
        try:
            pr = effects.publish(branch, payload["delivery_id"], digest)
        except AdapterError as exc:
            if exc.safe_message == "create-race":
                owned = effects.discover(branch, payload["delivery_id"])
                if len(owned) == 1 and owned[0].get("digest") == digest and owned[0].get("draft") and owned[0].get("state") == "OPEN":
                    return Outcome(_result(payload, started, "duplicate-reused", "none", None,
                                           branch=branch, pr=owned[0]["url"], validation="passed", tests="passed"), payload["source_issue"])
            raise
        return Outcome(_result(payload, started, "draft-pr-created", "none", None,
                               branch=branch, pr=pr, validation="passed", tests="passed"), payload["source_issue"])
    except AdapterError as exc:
        return Outcome(_result(parsed, started, exc.status, exc.category, exc.safe_message), parsed.get("source_issue"))


class GitHubEffects:
    def _gh(self, *args: str) -> str:
        env = {k: v for k, v in os.environ.items() if k in SAFE_ENV}
        env["GH_TOKEN"] = os.environ["TARGET_PUBLICATION_TOKEN"]
        return subprocess.check_output(["gh", *args], text=True, env=env, stderr=subprocess.DEVNULL)

    def discover(self, branch: str, delivery_id: str) -> list[dict[str, Any]]:
        raw = self._gh("pr", "list", "--repo", TARGET, "--state", "all", "--head", branch,
                       "--json", "url,state,isDraft,body")
        found = []
        pattern = re.compile(rf"<!--\s*{MARKER}:\s*{re.escape(delivery_id)};\s*payload-sha256:\s*([0-9a-f]{{64}})\s*-->")
        for pr in json.loads(raw):
            match = pattern.search(pr.get("body") or "")
            if match:
                found.append({"url": pr["url"], "state": pr["state"], "draft": pr["isDraft"], "digest": match.group(1)})
            else:
                found.append({"url": pr["url"], "state": pr["state"], "draft": pr["isDraft"], "digest": "conflict"})
        return found

    def codex(self, instructions: str) -> None:
        Path(".codex-instructions.txt").write_text(instructions)
        env = {k: v for k, v in os.environ.items() if k in SAFE_ENV or k.startswith("CODEX_") or k == "OPENAI_API_KEY"}
        proc = subprocess.run(["codex", "exec", "--sandbox", "workspace-write", "-C", str(ROOT), "-"],
                              input=instructions, text=True, env=env)
        Path(".codex-instructions.txt").unlink(missing_ok=True)
        if proc.returncode:
            raise AdapterError("codex-runtime", "Codex execution failed", "failed")

    def validate_candidate(self) -> tuple[bool, str]:
        env = {k: v for k, v in os.environ.items() if k in SAFE_ENV}
        commands = [
            ["python", "-m", "pytest"], ["python", "scripts/validate_release.py"],
            ["python", "scripts/verify_target_workflows.py", "--fixtures-only"], ["git", "diff", "--check"],
        ]
        for command in commands:
            if subprocess.run(command, cwd=ROOT, env=env).returncode:
                return False, "tests" if "pytest" in command else "validation"
        return True, "passed"

    def publish(self, branch: str, delivery_id: str, digest: str) -> str:
        env = {k: v for k, v in os.environ.items() if k in SAFE_ENV}
        token = os.environ["TARGET_PUBLICATION_TOKEN"]
        subprocess.run(["git", "checkout", "-b", branch], check=True, cwd=ROOT, env=env)
        subprocess.run(["git", "add", "-A"], check=True, cwd=ROOT, env=env)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT, env=env).returncode == 0:
            raise AdapterError("no-changes", "Codex produced no candidate changes", "no-changes")
        subprocess.run(["git", "-c", "user.name=ai-sdlc-target", "-c", "user.email=ai-sdlc@users.noreply.github.com",
                        "commit", "-m", f"AI-SDLC delivery {delivery_id}"], check=True, cwd=ROOT, env=env)
        remote = f"https://x-access-token:{token}@github.com/{TARGET}.git"
        pushed = subprocess.run(["git", "push", remote, f"HEAD:refs/heads/{branch}"], cwd=ROOT, env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if pushed.returncode:
            raise AdapterError("publication", "create-race")
        body = f"<!-- {MARKER}: {delivery_id}; payload-sha256: {digest} -->\n\nAutomated draft; human review and merge are required."
        try:
            return self._gh("pr", "create", "--repo", TARGET, "--draft", "--head", branch, "--title",
                            f"AI-SDLC delivery {delivery_id}", "--body", body).strip()
        except subprocess.CalledProcessError:
            raise AdapterError("publication", "create-race")


def main() -> int:
    raw = os.environ.get("EXECUTION_INPUT_JSON", "")
    registry = json.loads((ROOT / "config/codex-repositories.json").read_text())
    outcome = run_adapter(raw, os.environ.get("CONCURRENCY_GROUP", ""), os.environ.get("CALLER_LOGIN", ""),
                          {x.strip() for x in os.environ.get("TRUSTED_CALLERS", "").split(",") if x.strip()},
                          registry, GitHubEffects())
    output = json.dumps(outcome.result, sort_keys=True, separators=(",", ":"))
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as handle:
            handle.write(f"execution_result={output}\nsource_issue={outcome.source_issue or ''}\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
