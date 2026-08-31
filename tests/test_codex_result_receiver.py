import json
from pathlib import Path

import pytest
from scripts.codex_result_receiver import (
    ADMISSION,
    FORWARDED,
    GitHubJournal,
    JournalComment,
    ReceiverError,
    load_trusted_authors,
    marker,
    receive,
)
from scripts.run_tc_mvp_ci_001 import run

ROOT = Path(__file__).resolve().parents[1]
RESULT = json.loads((ROOT / 'contracts/examples/valid-execution-result.json').read_text())
SOURCE = 'Young-Consultations/portfolio-tasks#42'


class FakeJournal:
    def __init__(self, *, authorized=True):
        self.authorized = authorized
        self.entries = [JournalComment(marker(ADMISSION, {key: value for key, value in {
            'contract_version': RESULT['contract_version'], 'delivery_id': RESULT['delivery_id'],
            'correlation_id': RESULT['correlation_id'], 'source_issue': SOURCE,
            'target_repository': RESULT['target_repository'],
        }.items()}), 'router-bot')]
        self.projections = []
        self.fail_forward = False
    def authenticate(self, repository):
        if not self.authorized: raise ReceiverError('authentication', 'denied')
    def comments(self, repository, issue): return list(self.entries)
    def trusted_author(self, author, role):
        return author == ('router-bot' if role == 'admission' else 'receiver-bot')
    def append(self, repository, issue, body): self.entries.append(JournalComment(body, 'receiver-bot'))
    def forward(self, repository, projection):
        if self.fail_forward: raise OSError('transient dispatch failure')
        self.projections.append(projection)


def test_receiver_authenticates_binds_records_and_forwards_failure_without_reinterpretation():
    result = dict(RESULT, execution_status='failed', failure_category='codex-runtime', failure_message='safe failure')
    journal = FakeJournal()
    receipt = receive(json.dumps(result), SOURCE, RESULT['target_repository'], journal)
    assert receipt.accepted and receipt.execution_status == 'failed'
    assert len(journal.projections) == 1
    assert 'safe failure' not in journal.entries[-1].body


def test_receiver_rejects_wrong_caller_before_projection():
    journal = FakeJournal()
    with pytest.raises(ReceiverError, match='caller'):
        receive(json.dumps(RESULT), SOURCE, 'Young-Consultations/slugger', journal)
    assert not journal.projections


def test_identical_result_is_noop_and_conflict_is_ambiguous():
    journal = FakeJournal()
    receive(json.dumps(RESULT), SOURCE, RESULT['target_repository'], journal)
    assert receive(json.dumps(RESULT), SOURCE, RESULT['target_repository'], journal).duplicate
    changed = dict(RESULT, workflow_url='https://github.com/Young-Consultations/portfolio-tasks/actions/runs/999')
    with pytest.raises(ReceiverError) as error:
        receive(json.dumps(changed), SOURCE, RESULT['target_repository'], journal)
    assert error.value.ambiguous and len(journal.projections) == 1


def test_duplicate_reused_for_same_managed_draft_is_equivalent_noop():
    created = dict(
        RESULT,
        execution_status='draft-pr-created',
        failure_category='none',
        failure_message=None,
        branch_name='codex/delivery-001',
        pull_request_url='https://github.com/Young-Consultations/consulting-playbook/pull/7',
        validation_result='passed',
        test_result='passed',
    )
    journal = FakeJournal()
    receive(json.dumps(created), SOURCE, RESULT['target_repository'], journal)

    reused = dict(
        created,
        execution_status='duplicate-reused',
        workflow_url='https://github.com/Young-Consultations/consulting-playbook/actions/runs/999',
        started_at='2099-01-01T00:00:00Z',
        completed_at='2099-01-01T00:00:01Z',
    )
    receipt = receive(json.dumps(reused), SOURCE, RESULT['target_repository'], journal)
    assert receipt.accepted and receipt.duplicate
    assert receipt.execution_status == 'duplicate-reused'
    assert len(journal.projections) == 1


def test_duplicate_reused_with_different_draft_is_ambiguous():
    created = dict(
        RESULT,
        execution_status='draft-pr-created',
        failure_category='none',
        failure_message=None,
        branch_name='codex/delivery-001',
        pull_request_url='https://github.com/Young-Consultations/consulting-playbook/pull/7',
        validation_result='passed',
        test_result='passed',
    )
    journal = FakeJournal()
    receive(json.dumps(created), SOURCE, RESULT['target_repository'], journal)
    reused = dict(created, execution_status='duplicate-reused', pull_request_url='https://github.com/Young-Consultations/consulting-playbook/pull/8')
    with pytest.raises(ReceiverError) as error:
        receive(json.dumps(reused), SOURCE, RESULT['target_repository'], journal)
    assert error.value.ambiguous and len(journal.projections) == 1


def test_recorded_receipt_retries_projection_until_forwarded_marker_exists():
    journal = FakeJournal()
    journal.fail_forward = True
    with pytest.raises(OSError, match='transient'):
        receive(json.dumps(RESULT), SOURCE, RESULT['target_repository'], journal)
    assert any('result-receipt' in entry.body for entry in journal.entries)
    assert not any(FORWARDED in entry.body for entry in journal.entries)
    journal.fail_forward = False
    assert not receive(json.dumps(RESULT), SOURCE, RESULT['target_repository'], journal).duplicate
    assert len(journal.projections) == 1
    assert receive(json.dumps(RESULT), SOURCE, RESULT['target_repository'], journal).duplicate


def test_untrusted_markers_cannot_bind_or_conflict_with_delivery():
    journal = FakeJournal()
    journal.entries[0] = JournalComment(journal.entries[0].body, 'attacker')
    with pytest.raises(ReceiverError, match='admitted'):
        receive(json.dumps(RESULT), SOURCE, RESULT['target_repository'], journal)


def test_result_writer_cannot_forge_an_admission_marker():
    journal = FakeJournal()
    journal.entries[0] = JournalComment(journal.entries[0].body, "receiver-bot")
    with pytest.raises(ReceiverError, match="admitted"):
        receive(json.dumps(RESULT), SOURCE, RESULT["target_repository"], journal)


def test_malformed_result_and_binding_fail_closed():
    journal = FakeJournal()
    with pytest.raises(ReceiverError): receive('{}', SOURCE, RESULT['target_repository'], journal)
    journal.entries.clear()
    with pytest.raises(ReceiverError, match='admitted'): receive(json.dumps(RESULT), SOURCE, RESULT['target_repository'], journal)
    assert not journal.projections


def test_receiver_requires_admission_from_its_exact_control_plane_release():
    journal = FakeJournal()
    with pytest.raises(ReceiverError, match="receiver release"):
        receive(
            json.dumps(RESULT), SOURCE, RESULT["target_repository"], journal,
            "ai-sdlc-v2.4.1",
        )
    binding = {
        "contract_version": RESULT["contract_version"],
        "delivery_id": RESULT["delivery_id"],
        "correlation_id": RESULT["correlation_id"],
        "source_issue": SOURCE,
        "target_repository": RESULT["target_repository"],
        "control_plane_release": "ai-sdlc-v2.4.1",
        "activation_revision": "a" * 40,
        "activation_sha256": "b" * 64,
    }
    journal.entries[0] = JournalComment(marker(ADMISSION, binding), "router-bot")
    assert receive(
        json.dumps(RESULT), SOURCE, RESULT["target_repository"], journal,
        "ai-sdlc-v2.4.1",
    ).accepted


def test_github_journal_reads_every_slurped_comment_page(monkeypatch, tmp_path):
    journal = GitHubJournal(write_trust_policy(tmp_path, ["router-bot"]))
    pages = [
        [{"body": f"comment-{index}", "user": {"login": "router-bot"}} for index in range(100)],
        [{"body": "comment-100", "user": {"login": "router-bot"}}],
    ]
    monkeypatch.setattr(journal, "_api", lambda *args, **kwargs: pages)
    comments = journal.comments("Young-Consultations/portfolio-tasks", 42)
    assert len(comments) == 101
    assert comments[-1].body == "comment-100"


def test_github_journal_treats_a_null_user_as_untrusted(monkeypatch, tmp_path):
    journal = GitHubJournal(write_trust_policy(tmp_path, ["router-bot"]))
    monkeypatch.setattr(
        journal, "_api", lambda *args, **kwargs: [[{"body": "marker", "user": None}]]
    )
    assert journal.comments("Young-Consultations/portfolio-tasks", 42) == [
        JournalComment("marker", "")
    ]


def write_trust_policy(tmp_path, admission_authors, result_authors=None):
    path = tmp_path / "codex-result-trust.json"
    path.write_text(json.dumps({
        "policy_format_version": 2,
        "trusted_admission_authors": admission_authors,
        "trusted_result_authors": result_authors if result_authors is not None else ["receiver-app[bot]"],
    }))
    return path


def test_receiver_loads_trusted_authors_from_control_plane_policy(tmp_path, monkeypatch):
    policy = write_trust_policy(tmp_path, ["router-app[bot]"], ["receiver-app[bot]"])
    monkeypatch.setenv("CODEX_TRUSTED_JOURNAL_AUTHORS", "attacker")

    assert load_trusted_authors(policy) == {"admission": {"router-app[bot]"}, "result": {"receiver-app[bot]"}}
    assert GitHubJournal(policy).trusted_author("ROUTER-APP[BOT]", "admission")
    assert not GitHubJournal(policy).trusted_author("attacker", "admission")


@pytest.mark.parametrize(("admission_authors", "result_authors"), [
    ([], ["receiver"]), (["bad author"], ["receiver"]),
    (["bot", "BOT"], ["receiver"]), (["same"], ["SAME"]),
])
def test_receiver_trust_policy_fails_closed(tmp_path, admission_authors, result_authors):
    with pytest.raises(ReceiverError, match="trust policy"):
        load_trusted_authors(write_trust_policy(tmp_path, admission_authors, result_authors))


def test_tc_mvp_ci_001_complete_no_effect_oracle():
    assert run() == []
