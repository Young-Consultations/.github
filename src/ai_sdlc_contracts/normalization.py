"""Conservative legacy spelling normalization."""

from typing import Any, Dict, Mapping, Optional

from .models import MigrationMappings

_SAFE_MAPPINGS: MigrationMappings = {
    "priority": {"P0": "p0", "P1": "p1", "P2": "p2", "P3": "p3"},
    "executor": {"Codex": "codex"},
    "status": {"Draft PR": "draft-pr"},
}


def normalize_payload(
    payload: Mapping[str, Any], *, migration_mappings: Optional[MigrationMappings] = None
) -> Dict[str, Any]:
    """Return a shallow normalized copy, applying only explicit value mappings.

    Callers may provide task-type migrations when their legacy vocabulary is
    unambiguous. No task-type mapping is enabled by default.
    """
    normalized = dict(payload)
    mappings: Dict[str, Mapping[str, str]] = dict(_SAFE_MAPPINGS)
    if migration_mappings:
        mappings.update(migration_mappings)
    for field, values in mappings.items():
        value = normalized.get(field)
        if isinstance(value, str) and value in values:
            normalized[field] = values[value]
    return normalized
