"""Canonical construction of task contracts from structured GitHub issues."""

import re
from enum import Enum
from typing import Dict, List, Mapping, Optional, Tuple

from .errors import ContractValidationError, TaskContractBuildError
from .loader import load_contract_version
from .validator import validate_task


class ExecutionMode(str, Enum):
    """Modes accepted by the reusable execution router."""

    VERIFY = "verify"
    IMPLEMENT = "implement"


_REPOSITORY = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}$")
_TASK_TYPES = {
    "automation",
    "backlog-governance",
    "ci-cd",
    "documentation",
    "repository-maintenance",
    "feature",
    "bug-fix",
    "testing",
    "security",
}
_FIELD_NAMES = {
    "target repository",
    "executor",
    "task type",
    "priority",
    "execution status",
    "status",
    "project",
    "parallel safe",
    "dependencies",
    "risk",
    "scope",
    "objective",
    "current behavior",
    "required behavior",
    "in-scope files",
    "out-of-scope files",
    "architectural constraints",
    "constraints",
    "acceptance criteria",
    "testing requirements",
    "definition of done",
    "instructions",
    "created by",
}


def _structured_fields(body: str) -> Dict[str, str]:
    """Parse second-level Markdown headings and bold ``Name:`` fields."""
    fields: Dict[str, str] = {}
    current: Optional[str] = None
    content: List[str] = []

    def finish() -> None:
        if current is not None:
            value = "\n".join(content).strip()
            if value:
                fields[current] = value

    for line in body.splitlines():
        heading = re.match(r"^#{2,6}\s+(.+?)\s*$", line)
        bold = re.match(r"^\s*\*\*(.+?):\*\*\s*(.*)$", line)
        match: Optional[Tuple[str, str]] = None
        if heading:
            name = heading.group(1).strip().lower()
            if name in _FIELD_NAMES:
                match = (name, "")
        elif bold:
            name = bold.group(1).strip().lower()
            if name in _FIELD_NAMES:
                match = (name, bold.group(2).strip())
        if match:
            finish()
            current, initial = match
            content = [initial] if initial else []
        elif current is not None:
            content.append(line)
    finish()
    return fields


def _required(fields: Mapping[str, str], name: str) -> str:
    value = fields.get(name, "").strip()
    if not value:
        raise TaskContractBuildError(f"missing required structured field: {name}")
    return value


def _execution_status(fields: Mapping[str, str]) -> str:
    """Return an explicitly supplied execution status from a supported field."""
    for name in ("execution status", "status"):
        value = fields.get(name, "").strip()
        if value:
            return _scalar(value).lower()
    raise TaskContractBuildError(
        "missing required structured field: execution status or status"
    )


def _scalar(value: str) -> str:
    """Remove common Markdown list/inline-code decoration from a scalar."""
    first = next((line.strip() for line in value.splitlines() if line.strip()), "")
    return re.sub(r"^[-*]\s+", "", first).strip().strip("`")


def _boolean(value: str, field: str) -> bool:
    normalized = _scalar(value).lower()
    if normalized in {"true", "yes"}:
        return True
    if normalized in {"false", "no"}:
        return False
    raise TaskContractBuildError(f"invalid structured field: {field}")


def _dependencies(value: str) -> List[str]:
    normalized = _scalar(value)
    if normalized.lower() in {"", "none", "n/a", "[]"}:
        return []
    return [item.strip() for item in re.split(r"[,\n]", value) if item.strip()]


def _issue_metadata(issue: Mapping[str, object]) -> Tuple[int, str, str]:
    number = issue.get("number")
    title = issue.get("title")
    body = issue.get("body")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise TaskContractBuildError("invalid GitHub issue field: number")
    if not isinstance(title, str) or not title.strip():
        raise TaskContractBuildError("invalid GitHub issue field: title")
    if not isinstance(body, str) or not body.strip():
        raise TaskContractBuildError("missing or malformed GitHub issue body")
    labels, state, url = issue.get("labels"), issue.get("state"), issue.get("html_url")
    if not isinstance(labels, list):
        raise TaskContractBuildError("invalid GitHub issue field: labels")
    if not isinstance(state, str) or not state:
        raise TaskContractBuildError("invalid GitHub issue field: state")
    if not isinstance(url, str) or not url:
        raise TaskContractBuildError("invalid GitHub issue field: html_url")
    return number, title.strip(), body


def build_task_contract_from_issue(
    *,
    source_repository: str,
    issue: Mapping[str, object],
    execution_mode: ExecutionMode,
) -> Dict[str, object]:
    """Build and schema-validate a canonical task contract from a GitHub issue."""
    if not _REPOSITORY.fullmatch(source_repository):
        raise TaskContractBuildError("invalid source repository")
    if not isinstance(execution_mode, ExecutionMode):
        raise TaskContractBuildError("unsupported execution mode")
    if not isinstance(issue, Mapping):
        raise TaskContractBuildError("issue JSON must contain a GitHub issue object")
    number, title, body = _issue_metadata(issue)
    fields = _structured_fields(body)
    target = _scalar(_required(fields, "target repository"))
    task_type = _scalar(_required(fields, "task type")).lower()
    if task_type not in _TASK_TYPES:
        raise TaskContractBuildError("unsupported task type")

    status = _execution_status(fields)
    intent_sections = (
        "objective",
        "current behavior",
        "required behavior",
        "in-scope files",
        "out-of-scope files",
        "architectural constraints",
    )
    trailing_sections = (
        "constraints",
        "acceptance criteria",
        "testing requirements",
        "definition of done",
    )
    # Extended issue templates are rendered as a lossless, structured
    # implementation specification so downstream AI executors see every part.
    if any(fields.get(name) for name in intent_sections):
        instruction_parts = []
        if fields.get("instructions"):
            instruction_parts.append(f"## Instructions\n{fields['instructions']}")
        for name in (*intent_sections, *trailing_sections):
            if fields.get(name):
                instruction_parts.append(f"## {name.title()}\n{fields[name]}")
    else:
        # Retain the byte-for-byte instruction format used by legacy issues.
        instruction_parts = [fields.get("instructions", title)]
        for name in trailing_sections:
            if fields.get(name):
                instruction_parts.append(f"{name.title()}:\n{fields[name]}")
    contract: Dict[str, object] = {
        "contract_version": load_contract_version(),
        "task_id": f"{source_repository.replace('/', '-')}-{number}",
        "source_issue": f"{source_repository}#{number}",
        "status": status,
        "executor": _scalar(fields.get("executor", "codex")).lower(),
        "project": _scalar(fields.get("project", target.split("/", 1)[-1])),
        "priority": _scalar(fields.get("priority", "p2")).lower(),
        "task_type": task_type,
        "target_repository": target,
        "parallel_safe": _boolean(
            fields.get("parallel safe", "false"), "parallel safe"
        ),
        "dependencies": _dependencies(fields.get("dependencies", "none")),
        "risk": _scalar(fields.get("risk", "low")).lower(),
        "scope": _scalar(fields.get("scope", "small")).lower(),
        "instructions": "\n\n".join(
            part.strip() for part in instruction_parts if part.strip()
        ),
        "created_by": _scalar(fields.get("created by", "chatgpt-planning")),
    }
    try:
        validate_task(contract)
    except ContractValidationError as exc:
        raise TaskContractBuildError(f"task contract schema {exc}") from exc
    return contract
