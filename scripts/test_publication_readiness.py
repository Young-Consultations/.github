"""Shared credential-free readiness contract tests (no GitHub or model calls)."""
import hashlib
import json
import unittest
from datetime import datetime, timezone

from publication_readiness import ReadinessError, require_readiness

NOW = datetime(2026, 11, 24, tzinfo=timezone.utc)
TOKEN = "synthetic-publication-only"
EXPECTED = dict(repository="Example/target", executor_sha="a" * 40,
                control_plane_sha="b" * 40, environment="protected",
                receiver_ref="ai-sdlc-v4.0.0", policy_revision="1")


def record(**changes):
    value = dict(EXPECTED, version=1, credential_sha256=hashlib.sha256(TOKEN.encode()).hexdigest(),
                 verified_at="2026-11-23T00:00:00Z", outcome="draft-pr-created",
                 draft_url="https://github.com/Example/target/pull/7")
    value.update(changes)
    return json.dumps(value)


class ReadinessTests(unittest.TestCase):
    def test_valid(self):
        require_readiness(record(), EXPECTED, TOKEN, now=NOW)

    def test_missing_or_malformed(self):
        for raw in ("", "[]", "{}", "null", '{"version":1,"version":1}', record(version=True), record(extra="secret")):
            with self.subTest(raw=raw[:15]), self.assertRaises(ReadinessError):
                require_readiness(raw, EXPECTED, TOKEN, now=NOW)

    def test_each_binding(self):
        for key in EXPECTED:
            with self.subTest(key=key), self.assertRaises(ReadinessError):
                require_readiness(record(**{key: "wrong"}), EXPECTED, TOKEN, now=NOW)

    def test_denied_or_indeterminate(self):
        for changes in ({"outcome": "denied"}, {"outcome": "unknown"}, {"draft_url": "https://github.com/Other/repo/pull/7"}):
            with self.subTest(changes=changes), self.assertRaises(ReadinessError):
                require_readiness(record(**changes), EXPECTED, TOKEN, now=NOW)

    def test_time(self):
        for verified in ("2026-10-24T00:00:00Z", "2026-11-25T00:00:00Z", "invalid"):
            with self.subTest(verified=verified), self.assertRaises(ReadinessError):
                require_readiness(record(verified_at=verified), EXPECTED, TOKEN, now=NOW)
        require_readiness(record(verified_at="2026-10-25T00:00:00Z"), EXPECTED, TOKEN, now=NOW)

    def test_rotation_and_empty_policy(self):
        for token in ("", "new-token"):
            with self.assertRaises(ReadinessError):
                require_readiness(record(), EXPECTED, token, now=NOW)
        with self.assertRaises(ReadinessError):
            require_readiness(record(), dict(EXPECTED, policy_revision=""), TOKEN, now=NOW)

    def test_no_raw_evidence_in_errors(self):
        with self.assertRaises(ReadinessError) as exc:
            require_readiness("private-value", EXPECTED, TOKEN, now=NOW)
        self.assertNotIn("private-value", str(exc.exception))
        self.assertNotIn(TOKEN, str(exc.exception))


if __name__ == "__main__":
    unittest.main()
