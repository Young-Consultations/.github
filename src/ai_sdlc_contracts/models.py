"""Shared typing primitives (schemas remain the source of truth)."""

from typing import Any, Mapping, TypeAlias

Payload: TypeAlias = Mapping[str, Any]
MigrationMappings: TypeAlias = Mapping[str, Mapping[str, str]]
