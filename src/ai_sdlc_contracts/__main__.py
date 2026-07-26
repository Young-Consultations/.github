"""Command-line interface for contract validation."""

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Mapping, Any, Optional, Sequence

from . import ContractSchemaLoadError, ContractValidationError
from .validator import validate_execution_input, validate_execution_result, validate_task


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-sdlc-contracts")
    parser.add_argument("command", choices=("validate-task", "validate-input", "validate-result"))
    parser.add_argument("payload", type=Path)
    args = parser.parse_args(argv)
    validators: Mapping[str, Callable[[Mapping[str, Any]], None]] = {
        "validate-task": validate_task,
        "validate-input": validate_execution_input,
        "validate-result": validate_execution_result,
    }
    try:
        payload = json.loads(args.payload.read_text(encoding="utf-8"))
        validators[args.command](payload)
    except (OSError, json.JSONDecodeError):
        print("error: payload file could not be read as JSON", file=sys.stderr)
        return 2
    except (ContractValidationError, ContractSchemaLoadError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
