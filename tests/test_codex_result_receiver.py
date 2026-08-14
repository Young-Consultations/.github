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
        }.items()}), 'trusted-bot')]
        self.projections = []
        self.fail_forward = False
    def authenticate(self, repository):
        if not self.authorized: raise ReceiverError('authentication', 'denied')
    def comments(self, repository, issue): return list(self.entries)
    def trusted_author(self, author): return author == 'trusted-bot'
    def append(self, repository, issue, body): self.entries.append(JournalComment(body, 'trusted-bot'))
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


def test_malformed_result_and_binding_fail_closed():
    journal = FakeJournal()
    with pytest.raises(ReceiverError): receive('{}', SOURCE, RESULT['target_repository'], journal)
    journal.entries.clear()
    with pytest.raises(ReceiverError, match='admitted'): receive(json.dumps(RESULT), SOURCE, RESULT['target_repository'], journal)
    assert not journal.projections


def write_trust_policy(tmp_path, authors):
    path = tmp_path / "codex-result-trust.json"
    path.write_text(json.dumps({
        "policy_format_version": 1,
        "trusted_journal_authors": authors,
    }))
    return path


def test_receiver_loads_trusted_authors_from_control_plane_policy(tmp_path, monkeypatch):
    policy = write_trust_policy(tmp_path, ["router-app[bot]", "receiver-app[bot]"])
    monkeypatch.setenv("CODEX_TRUSTED_JOURNAL_AUTHORS", "attacker")

    assert load_trusted_authors(policy) == {"router-app[bot]", "receiver-app[bot]"}
    assert GitHubJournal(policy).trusted_author("ROUTER-APP[BOT]")
    assert not GitHubJournal(policy).trusted_author("attacker")


@pytest.mark.parametrize("authors", [[], ["bad author"], ["bot", "BOT"]])
def test_receiver_trust_policy_fails_closed(tmp_path, authors):
    with pytest.raises(ReceiverError, match="trust policy"):
        load_trusted_authors(write_trust_policy(tmp_path, authors))


def test_tc_mvp_ci_001_complete_no_effect_oracle():
    assert run() == []
