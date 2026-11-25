"""DEF-0151 / #111: synthetic router -> preflight -> target -> receiver regression.

The registered adapter is loaded only after read-only checkout identity checks.
All subsequent GH/process/socket calls are either explicitly emulated or trapped.
The historical source #167 is never used, read, or dispatched by this suite.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
from unittest.mock import patch

import pytest

from scripts import codex_result_credential_preflight as preflight
from scripts import codex_result_receiver as receiver
from scripts import codex_router as router
from scripts import run_tc_mvp_e2e_001 as e2e


SOURCE = "Young-Consultations/portfolio-tasks#999999"
REPOSITORY, ISSUE = SOURCE.split("#")
TARGET = e2e.REAL_TARGET
RELEASE = f"ai-sdlc-v{e2e.CANDIDATE_RELEASE}"


class SyntheticGitHub:
    """One journal for actual router, preflight and receiver code."""

    def __init__(self):
        self.authors = receiver.load_trusted_authors()
        self.admission_author = sorted(self.authors["admission"])[0]
        self.result_author = sorted(self.authors["result"])[0]
        self.records = {}
        self.next_id = 100
        self.dispatches = []
        self.projections = []
        self.external_attempts = []
        self.probes = 0
        self.unreadable = False
        self.fail_forward = False

    def add(self, body, author):
        self.next_id += 1
        self.records[self.next_id] = {
            "id": self.next_id, "body": body, "user": {"login": author},
        }
        return self.records[self.next_id]

    def trap(self, *args, **kwargs):
        self.external_attempts.append("unexpected external call")
        pytest.fail("external process or network access forbidden")

    def run(self, cmd, **kwargs):
        """Emulate only the exact router comment and dispatch commands."""
        endpoint = f"repos/{REPOSITORY}/issues/{ISSUE}/comments"
        if cmd == ["gh", "api", "--paginate", "--slurp", endpoint + "?per_page=100"]:
            value = [list(self.records.values())]
        elif cmd[:6] == ["gh", "api", endpoint, "--method", "POST", "-f"] and len(cmd) == 7:
            assert cmd[6].startswith("body=" + receiver.ADMISSION)
            value = self.add(cmd[6][5:], self.admission_author)
        elif (
            len(cmd) == 5 and cmd[:2] == ["gh", "api"]
            and cmd[2].startswith(f"repos/{REPOSITORY}/issues/comments/")
            and cmd[3:] == ["--method", "DELETE"]
        ):
            record_id = int(cmd[2].rsplit("/", 1)[1])
            assert self.records[record_id]["user"]["login"] == self.admission_author
            assert self.records[record_id]["body"].startswith(receiver.ADMISSION)
            del self.records[record_id]
            value = None
        elif cmd[:3] == ["gh", "workflow", "run"]:
            workflow, ref = router.parse_workflow_ref(TARGET, e2e._registry_entry()["workflow_ref"])
            assert cmd[:8] == ["gh", "workflow", "run", workflow, "--repo", TARGET, "--ref", ref]
            assert len(cmd) == 12 and cmd[8] == cmd[10] == "-f"
            assert cmd[9].startswith("execution_input_json=")
            payload = json.loads(cmd[9].split("=", 1)[1])
            assert payload["source_issue"] == SOURCE
            assert payload["target_repository"] == TARGET
            assert cmd[11] == "concurrency_group=" + payload["concurrency_group"]
            self.dispatches.append(payload)
            value = None
        else:
            return self.trap()
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(value) if value is not None else "")

    def authenticate(self, repository, issue):
        assert (repository, issue) == (REPOSITORY, int(ISSUE))

    def comments(self, repository, issue):
        self.authenticate(repository, issue)
        if self.unreadable:
            raise OSError("synthetic journal unavailable")
        return [receiver.JournalComment(r["body"], r["user"]["login"]) for r in self.records.values()]

    def trusted_author(self, author, role):
        return author.casefold() in self.authors[role]

    def probe_forward(self, repository):
        assert repository == REPOSITORY
        self.probes += 1

    def append(self, repository, issue, body):
        self.authenticate(repository, issue)
        self.add(body, self.result_author)

    def forward(self, repository, projection):
        assert repository == REPOSITORY and projection["source_issue"] == SOURCE
        if self.fail_forward:
            raise OSError("synthetic forwarding failed before effect")
        self.projections.append(projection)

    def evidence(self, prefix):
        return receiver.parse_markers(
            self.comments(REPOSITORY, int(ISSUE)), prefix,
            "admission" if prefix == receiver.ADMISSION else "result", self,
        )

    def synthetic_receipt(self, payload, effect, *, author=None, **overrides):
        evidence = {k: payload[k] for k in preflight._BINDING_FIELDS}
        evidence.update(effect_class=effect, result_sha256="a" * 64, effect_sha256="b" * 64)
        evidence.update(overrides)
        self.add(receiver.marker(receiver.RECEIPT, evidence), author or self.result_author)


class Effects(e2e.FakeTargetEffects):
    def __init__(self, adapter, *, found=None, fail=False):
        super().__init__(adapter, e2e.EffectTraps(), found=found)
        self.prepared = 0
        self.fail = fail

    def prepare_content(self, delivery_id, timeout_seconds):
        self.prepared += 1
        super().prepare_content(delivery_id, timeout_seconds)

    def codex(self, instructions, timeout_seconds):
        super().codex(instructions, timeout_seconds)
        if self.fail:
            raise self.adapter.AdapterError("codex-runtime", "synthetic provider failure", "failed")


@pytest.fixture(scope="module")
def adapter():
    raw = os.environ.get(e2e.TARGET_ROOT_ENV)
    if not raw:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("registered adapter checkout is mandatory in CI")
        pytest.skip("set TC_MVP_E2E_TARGET_ROOT to the exact registered adapter checkout")
    root = e2e._target_root()
    assert e2e._target_identity_errors(root) == []
    assert e2e._target_receiver_pin_errors(root) == []
    # Importing adapter code is also inside the credential-free process trap.
    def denied(*args, **kwargs):
        pytest.fail("unexpected external call during adapter import")
    with patch.dict(os.environ, {}, clear=True), patch.object(subprocess, "run", denied), \
            patch.object(subprocess, "Popen", denied), patch.object(socket, "socket", denied), \
            patch.object(socket, "create_connection", denied):
        module = e2e._load_target_adapter(root)
    assert module.TARGET == TARGET
    return module


@pytest.fixture
def github(monkeypatch):
    journal = SyntheticGitHub()
    with patch.dict(os.environ, {}, clear=True):
        monkeypatch.setattr(subprocess, "run", journal.run)
        for name in ("Popen", "check_output", "call", "check_call"):
            monkeypatch.setattr(subprocess, name, journal.trap)
        for name in ("socket", "create_connection", "getaddrinfo"):
            monkeypatch.setattr(socket, name, journal.trap)
        for name in ("system", "popen", "execve", "posix_spawn", "posix_spawnp"):
            if hasattr(os, name):
                monkeypatch.setattr(os, name, journal.trap)
        monkeypatch.setattr(preflight, "GitHubJournal", lambda: journal)
        yield journal
        assert journal.external_attempts == []


def admit(github, identity="synthetic-def-0151-a"):
    task = e2e._task()
    task.update(task_id=identity, source_issue=SOURCE, instructions="Synthetic replay regression only.")
    route = e2e._route_task(task)
    payload = route["execution_input"]
    assert route["validation_result"] == "passed"
    assert payload["delivery_id"] == payload["correlation_id"] == identity
    with patch.dict(os.environ, {
        "EXECUTION_INPUT": json.dumps(payload),
        "WORKFLOW_REF": route["workflow_ref"],
        "CONTROL_PLANE_RELEASE": RELEASE,
        "CODEX_ACTIVATION_REVISION": "a" * 40,
        "CODEX_ACTIVATION_SHA256": "b" * 64,
        "GITHUB_OUTPUT": os.devnull,
    }, clear=True):
        router.dispatch()
    assert github.dispatches[-1] == payload
    matches = [r for r in github.evidence(receiver.ADMISSION) if r["delivery_id"] == identity]
    assert len(matches) == 1
    assert all(matches[0][k] == payload[k] for k in preflight._BINDING_FIELDS)
    return github.dispatches[-1]


def preflight_target(github, payload, effects, tmp_path):
    out = tmp_path / "preflight-output"
    out.unlink(missing_ok=True)
    probes = github.probes
    with patch.dict(os.environ, {
        "SOURCE_ISSUE": SOURCE, "EXECUTION_INPUT_JSON": json.dumps(payload),
        "GITHUB_OUTPUT": str(out),
    }, clear=True):
        code = preflight.main()
    if code:
        assert not out.exists()
        assert github.probes == probes
        assert_zero(effects, discovery=0)
        return None
    assert github.probes == probes + 1
    raw = out.read_text()
    assert raw in {"prior_effect_class=none\n", "prior_effect_class=managed-draft\n"}
    return e2e._run_target(effects.adapter, payload, effects, prior_result_effect=raw.strip().split("=", 1)[1])


def receive(github, result):
    return receiver.receive(json.dumps(result), SOURCE, TARGET, github, RELEASE)


def assert_zero(effects, *, discovery):
    assert effects.calls.discover_calls == discovery
    assert effects.calls.codex_calls == effects.calls.validation_calls == effects.calls.publication_calls == 0
    assert effects.prepared == 0


def test_actual_failed_result_blocks_same_delivery_and_fresh_identity_works(adapter, github, tmp_path, capsys):
    payload = admit(github)
    first = Effects(adapter, fail=True)
    result = preflight_target(github, payload, first, tmp_path)
    assert result["execution_status"] == "failed"
    assert result["failure_category"] == "codex-runtime"
    assert first.calls.codex_calls == first.prepared == 1
    assert first.calls.publication_calls == 0
    receipt = receive(github, result)
    assert receipt.accepted and not receipt.duplicate
    assert len(github.projections) == 1
    original = github.evidence(receiver.RECEIPT)
    assert original[0]["effect_class"] == "failed"

    assert admit(github) == payload
    retry = Effects(adapter)
    assert preflight_target(github, payload, retry, tmp_path) is None
    assert "terminal result; new authorization is required" in capsys.readouterr().err
    assert_zero(retry, discovery=0)
    assert github.evidence(receiver.RECEIPT) == original
    assert len(github.projections) == 1
    assert len(github.dispatches) == 2
    conflicting = dict(result, failure_message="different synthetic failure")
    with pytest.raises(receiver.ReceiverError, match="conflicting result") as exc:
        receive(github, conflicting)
    assert exc.value.ambiguous
    assert len(github.projections) == 1

    fresh = admit(github, "synthetic-def-0151-b")
    good = Effects(adapter)
    new_result = preflight_target(github, fresh, good, tmp_path)
    assert new_result["execution_status"] == "draft-pr-created"
    assert receive(github, new_result).accepted
    assert good.prepared == good.calls.codex_calls == good.calls.publication_calls == 1
    assert len(github.projections) == 2
    assert len(github.evidence(receiver.RECEIPT)) == 2


@pytest.mark.parametrize("effect", ["failed", "rejected", "ambiguous-rejected", "verified", "blocked"])
def test_prior_nonmanaged_terminal_receipt_denies_before_effects(adapter, github, tmp_path, capsys, effect):
    payload = admit(github)
    github.synthetic_receipt(payload, effect)
    original = dict(github.records)
    assert preflight_target(github, payload, Effects(adapter), tmp_path) is None
    assert "terminal result; new authorization is required" in capsys.readouterr().err
    assert github.records == original and not github.projections


@pytest.mark.parametrize("fault", [
    "unreadable", "conflicting", "wrong-binding", "bad-digest", "malformed",
    "missing-admission", "orphan-forwarding", "unbound",
])
def test_uncertain_journal_fails_closed(adapter, github, tmp_path, fault):
    payload = admit(github)
    if fault == "unreadable":
        github.unreadable = True
    elif fault == "conflicting":
        github.synthetic_receipt(payload, "failed")
        github.synthetic_receipt(payload, "managed-draft")
    elif fault == "wrong-binding":
        github.synthetic_receipt(payload, "managed-draft", correlation_id="other")
    elif fault == "bad-digest":
        github.synthetic_receipt(payload, "managed-draft", effect_sha256="invalid")
    elif fault == "malformed":
        github.add(receiver.RECEIPT + "broken", github.result_author)
    elif fault == "missing-admission":
        github.records.clear()
    elif fault == "orphan-forwarding":
        github.add(receiver.marker(receiver.FORWARDED, {"delivery_id": payload["delivery_id"]}), github.result_author)
    elif fault == "unbound":
        github.add(receiver.marker(receiver.RECEIPT, {"effect_class": "failed"}), github.result_author)
    original = dict(github.records)
    assert preflight_target(github, payload, Effects(adapter), tmp_path) is None
    assert github.records == original and not github.projections


@pytest.mark.parametrize("receipt_only", [False, True])
def test_actual_managed_draft_redelivery_reuses_without_second_model(adapter, github, tmp_path, receipt_only):
    payload = admit(github)
    # Marker-shaped text by an untrusted author must not prevent legitimate work.
    github.synthetic_receipt(payload, "failed", author="synthetic-untrusted-user")
    first = Effects(adapter)
    result = preflight_target(github, payload, first, tmp_path)
    assert result["execution_status"] == "draft-pr-created"
    assert first.calls.codex_calls == first.calls.publication_calls == 1
    if receipt_only:
        github.fail_forward = True
        with pytest.raises(OSError, match="synthetic forwarding"):
            receive(github, result)
        github.fail_forward = False
        assert len(github.projections) == 0
    else:
        assert receive(github, result).accepted
        assert len(github.projections) == 1
    assert admit(github) == payload
    retry = Effects(adapter, found=[e2e._managed(adapter, payload)])
    replay = preflight_target(github, payload, retry, tmp_path)
    assert replay["execution_status"] == "duplicate-reused"
    assert_zero(retry, discovery=1)
    receipt = receive(github, replay)
    assert receipt.accepted
    assert receipt.duplicate is (not receipt_only)
    assert len(github.projections) == len(github.evidence(receiver.RECEIPT)) == len(github.evidence(receiver.FORWARDED)) == 1


@pytest.mark.parametrize("conflict", [False, True])
def test_managed_receipt_without_proven_owned_draft_denies(adapter, github, tmp_path, conflict):
    payload = admit(github)
    github.synthetic_receipt(payload, "managed-draft")
    found = [dict(e2e._managed(adapter, payload), digest="c" * 64)] if conflict else []
    effects = Effects(adapter, found=found)
    result = preflight_target(github, payload, effects, tmp_path)
    assert result["execution_status"] == "ambiguous-rejected"
    assert_zero(effects, discovery=1)
    assert not github.projections


@pytest.mark.parametrize("classification", ["not-checked", "", "failed", "rejected", "ambiguous-rejected", "invalid"])
def test_direct_adapter_rejects_invalid_preflight_classification(adapter, github, classification):
    payload = admit(github)
    effects = Effects(adapter)
    result = e2e._run_target(adapter, payload, effects, prior_result_effect=classification)
    assert result["execution_status"] == "ambiguous-rejected"
    assert result["failure_category"] == "authorization"
    assert_zero(effects, discovery=0)
    assert not github.projections
