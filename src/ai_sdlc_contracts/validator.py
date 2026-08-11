"""Schema-backed validation entry points."""

from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .errors import ContractSchemaLoadError, ContractValidationError, UnsupportedContractVersionError
from .loader import load_contract_version, load_schema


def _path(error: Any, schema: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
    parts = [str(part) for part in error.absolute_path]
    if error.validator == "additionalProperties":
        allowed = set(schema.get("properties", {}))
        unknown = sorted(set(payload) - allowed)
        if unknown:
            parts.append(unknown[0])
    return "$" + "".join(f"[{part}]" if part.isdigit() else f".{part}" for part in parts)


def _validate(kind: str, payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ContractValidationError("validation failed at $: expected an object")
    expected = load_contract_version()
    supplied = payload.get("contract_version")
    if supplied is not None and supplied != expected:
        raise UnsupportedContractVersionError(
            "validation failed at $.contract_version: unsupported contract version"
        )
    schema = load_schema(kind)
    try:
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        error = next(iter(validator.iter_errors(payload)), None)
    except SchemaError as exc:
        raise ContractSchemaLoadError("canonical contract schema is invalid") from exc
    if error is not None:
        raise ContractValidationError(
            f"validation failed at {_path(error, schema, payload)}: "
            f"constraint '{error.validator}' was not satisfied"
        )


def validate_task(payload: Mapping[str, Any]) -> None:
    _validate("task", payload)


def validate_execution_input(payload: Mapping[str, Any]) -> None:
    _validate("input", payload)


def validate_execution_result(payload: Mapping[str, Any]) -> None:
    _validate("result", payload)
