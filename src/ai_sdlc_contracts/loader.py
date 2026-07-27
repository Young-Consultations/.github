"""Locate and load the canonical, repository-owned contract files."""

import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from .errors import ContractSchemaLoadError

SCHEMAS = {
    "task": "task-contract.schema.json",
    "input": "execution-input.schema.json",
    "result": "execution-result.schema.json",
}


def _contract_directory() -> Path:
    override = os.environ.get("AI_SDLC_CONTRACT_DIR")
    candidates = []
    if override:
        candidates.append(Path(override))
    candidates.append(Path(sys.prefix) / "share" / "ai-sdlc-contracts" / "contracts")

    # Support running directly from this repository without making discovery
    # depend on the caller's working directory.  Installed packages use the
    # data-files location above instead.
    package_directory = Path(__file__).resolve().parent
    if package_directory.parent.name == "src":
        candidates.append(package_directory.parent.parent / "contracts")

    for candidate in candidates:
        if (candidate / "contract-version.txt").is_file():
            return candidate
    raise ContractSchemaLoadError("canonical contract directory could not be located")


def load_contract_version() -> str:
    """Return the supported canonical contract version."""
    try:
        version = (_contract_directory() / "contract-version.txt").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ContractSchemaLoadError("contract version could not be loaded") from exc
    if not version:
        raise ContractSchemaLoadError("contract version is empty")
    return version


@lru_cache(maxsize=3)
def load_schema(kind: str) -> Dict[str, Any]:
    """Load a canonical JSON schema by payload kind."""
    try:
        filename = SCHEMAS[kind]
        value = json.loads((_contract_directory() / filename).read_text(encoding="utf-8"))
    except (KeyError, OSError, json.JSONDecodeError) as exc:
        raise ContractSchemaLoadError("canonical contract schema could not be loaded") from exc
    if not isinstance(value, dict):
        raise ContractSchemaLoadError("canonical contract schema is not an object")
    return value
