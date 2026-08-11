"""Command-line interface for validating canonical contracts."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from .errors import ContractSchemaLoadError, ContractValidationError
from .validator import validate_execution_input, validate_execution_result, validate_task


class _PayloadReadError(ValueError):
    """A validation input cannot be decoded."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-sdlc-contracts")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate-task", "validate-input", "validate-result"):
        validator = commands.add_parser(command, help=f"validate a {command.removeprefix('validate-')} payload")
        validator.add_argument("payload", type=Path)
    return parser


def _validate(command: str, payload_path: Path) -> None:
    validators: Mapping[str, Callable[[Mapping[str, Any]], None]] = {
        "validate-task": validate_task,
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
        _validate(args.command, args.payload)
    except _PayloadReadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ContractValidationError, ContractSchemaLoadError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
