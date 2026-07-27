"""Locate and load the canonical contract files."""

import json
import os
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any, Dict

from .errors import ContractSchemaLoadError

SCHEMAS = {
    "task": "task-contract.schema.json",
    "input": "execution-input.schema.json",
    "result": "execution-result.schema.json",
}


def _packaged_contract_directory():
    """Return the package-resource directory containing the contracts."""
    return files("ai_sdlc_contracts").joinpath("contracts")


def _source_contract_directory() -> Path:
    """Return the canonical directory when running from a source checkout."""
    return Path(__file__).resolve().parents[2] / "contracts"


def _read_contract_text(filename: str) -> str:
    override = os.environ.get("AI_SDLC_CONTRACT_DIR")
    if override:
        resources = (Path(override) / filename,)
    else:
        resources = (
            _packaged_contract_directory().joinpath(filename),
            _source_contract_directory() / filename,
        )

    for resource in resources:
        try:
            if resource.is_file():
                return resource.read_text(encoding="utf-8")
        except OSError:
            continue
    raise ContractSchemaLoadError("canonical contract resource could not be located")


def load_contract_version() -> str:
    """Return the supported canonical contract version."""
    try:
        version = _read_contract_text("contract-version.txt").strip()
    except (OSError, UnicodeError) as exc:
        raise ContractSchemaLoadError("contract version could not be loaded") from exc
    if not version:
        raise ContractSchemaLoadError("contract version is empty")
    return version


@lru_cache(maxsize=3)
def load_schema(kind: str) -> Dict[str, Any]:
    """Load a canonical JSON schema by payload kind."""
    try:
        filename = SCHEMAS[kind]
        value = json.loads(_read_contract_text(filename))
    except (KeyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractSchemaLoadError("canonical contract schema could not be loaded") from exc
    if not isinstance(value, dict):
        raise ContractSchemaLoadError("canonical contract schema is not an object")
    return value
