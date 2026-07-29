"""Command-line interface for constructing and validating contracts."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from . import ContractSchemaLoadError, ContractValidationError, TaskContractBuildError
from .builder import ExecutionMode, build_task_contract_from_issue
from .validator import (
    validate_execution_input,
    validate_execution_result,
    validate_task,
)


class _PayloadReadError(TaskContractBuildError):
    """A validation payload cannot be decoded."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-sdlc-contracts")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in (
        "validate-task",
        "validate-task-contract",
        "validate-input",
        "validate-result",
    ):
        validator = commands.add_parser(
            command, help=f"validate a {command.removeprefix('validate-')} payload"
        )
        validator.add_argument("payload", type=Path)
    build = commands.add_parser(
        "build-task-contract", help="build a task contract from a GitHub issue"
    )
    build.add_argument("--source-repository", required=True)
    build.add_argument("--issue-json", required=True, type=Path)
    build.add_argument(
        "--execution-mode",
        required=True,
        choices=[mode.value for mode in ExecutionMode],
    )
    build.add_argument("--output", required=True, type=Path)
    return parser


def _validate(command: str, payload_path: Path) -> None:
    validators: Mapping[str, Callable[[Mapping[str, Any]], None]] = {
        "validate-task": validate_task,
        "validate-task-contract": validate_task,
        "validate-input": validate_execution_input,
        "validate-result": validate_execution_result,
    }
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _PayloadReadError("payload file could not be read as JSON") from exc
    validators[command](payload)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build-task-contract":
            try:
                issue = json.loads(args.issue_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise TaskContractBuildError(
                    "issue file could not be read as JSON"
                ) from exc
            contract = build_task_contract_from_issue(
                source_repository=args.source_repository,
                issue=issue,
                execution_mode=ExecutionMode(args.execution_mode),
            )
            try:
                args.output.write_text(
                    json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False)
                    + "\n",
                    encoding="utf-8",
                )
            except OSError as exc:
                raise TaskContractBuildError(
                    "output file could not be written"
                ) from exc
            return 0
        _validate(args.command, args.payload)
    except _PayloadReadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (
        ContractValidationError,
        ContractSchemaLoadError,
        TaskContractBuildError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
