"""Shared typing primitives (schemas remain the source of truth)."""

from typing import Any, Mapping

Payload = Mapping[str, Any]
MigrationMappings = Mapping[str, Mapping[str, str]]
