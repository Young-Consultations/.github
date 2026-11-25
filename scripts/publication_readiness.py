"""Shared offline validation of owner-attested draft publication readiness."""
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone

MAX_AGE = timedelta(days=30)
BINDINGS = {"repository", "executor_sha", "control_plane_sha", "environment",
            "receiver_ref", "policy_revision"}


class ReadinessError(ValueError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReadinessError("Publication readiness evidence is malformed")
        result[key] = value
    return result


def require_readiness(raw, expected, token, *, now=None):
    """Reject missing, stale, denied or mismatched evidence without echoing it."""
    if not raw or not token:
        raise ReadinessError("Publication readiness evidence or credential is missing")
    try:
        record = json.loads(raw, object_pairs_hook=_unique)
    except (ValueError, TypeError, RecursionError):
        raise ReadinessError("Publication readiness evidence is malformed") from None
    fields = BINDINGS | {"version", "credential_sha256", "verified_at", "outcome", "draft_url"}
    if (not isinstance(record, dict) or set(record) != fields
            or type(record["version"]) is not int or record["version"] != 1
            or any(not isinstance(record[k], str) for k in fields - {"version"})):
        raise ReadinessError("Publication readiness evidence is malformed")
    if (set(expected) != BINDINGS or any(not isinstance(v, str) or not v for v in expected.values())
            or not re.fullmatch(r"[0-9a-f]{40}", expected["executor_sha"])
            or not re.fullmatch(r"[0-9a-f]{40}", expected["control_plane_sha"])
            or any(record[k] != expected[k] for k in BINDINGS)):
        raise ReadinessError("Publication readiness binding mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", record["credential_sha256"]) or not hmac.compare_digest(
            record["credential_sha256"], hashlib.sha256(token.encode()).hexdigest()):
        raise ReadinessError("Publication readiness credential changed")
    if (record["outcome"] != "draft-pr-created" or not re.fullmatch(
            r"https://github\.com/" + re.escape(expected["repository"]) + r"/pull/[1-9][0-9]*", record["draft_url"])):
        raise ReadinessError("Successful draft publication evidence is required")
    try:
        verified = datetime.strptime(record["verified_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ReadinessError("Publication readiness timestamp is invalid") from None
    age = (now or datetime.now(timezone.utc)) - verified
    if age < timedelta(0) or age > MAX_AGE:
        raise ReadinessError("Publication readiness evidence is stale or future-dated")
