import subprocess

from scripts import codex_result_credential_preflight as preflight


class AcceptingJournal:
    def __init__(self):
        self.authenticated = []
        self.forward_probes = []

    def authenticate(self, repository, issue):
        self.authenticated.append((repository, issue))

    def probe_forward(self, repository):
        self.forward_probes.append(repository)


class RejectingJournal:
    def authenticate(self, repository, issue):
        raise preflight.ReceiverError(
            "authentication",
            "result credential principal is not an approved result journal author",
        )

    def probe_forward(self, repository):
        raise AssertionError("must not probe forwarding after authentication failure")


class DispatchDeniedJournal(AcceptingJournal):
    def probe_forward(self, repository):
        raise subprocess.CalledProcessError(1, ["gh", "api"])


def test_preflight_accepts_trusted_result_writer_and_required_source_access(monkeypatch):
    journal = AcceptingJournal()
    monkeypatch.setenv(
        "SOURCE_ISSUE", "Young-Consultations/portfolio-tasks#42"
    )
    monkeypatch.setattr(preflight, "GitHubJournal", lambda: journal)

    assert preflight.main() == 0
    assert journal.authenticated == [("Young-Consultations/portfolio-tasks", 42)]
    assert journal.forward_probes == ["Young-Consultations/portfolio-tasks"]


def test_preflight_fails_closed_on_untrusted_result_writer(monkeypatch):
    monkeypatch.setenv(
        "SOURCE_ISSUE", "Young-Consultations/portfolio-tasks#42"
    )
    monkeypatch.setattr(preflight, "GitHubJournal", RejectingJournal)

    assert preflight.main() == 1


def test_preflight_fails_closed_without_repository_dispatch_write(monkeypatch):
    monkeypatch.setenv(
        "SOURCE_ISSUE", "Young-Consultations/portfolio-tasks#42"
    )
    monkeypatch.setattr(preflight, "GitHubJournal", DispatchDeniedJournal)

    assert preflight.main() == 1


def test_preflight_rejects_malformed_source_without_authentication(monkeypatch):
    monkeypatch.setenv("SOURCE_ISSUE", "not a source issue")
    monkeypatch.setattr(
        preflight,
        "GitHubJournal",
        lambda: (_ for _ in ()).throw(AssertionError("must not authenticate")),
    )

    assert preflight.main() == 1


# Receipt guard fixtures intentionally use exact trusted roles and bounded v2 identities.
from scripts.codex_result_receiver import (
    ADMISSION, FORWARDED, RECEIPT, JournalComment, marker,
)


INPUT_BINDING = {
    "contract_version": "ai-sdlc-contract/v2",
    "delivery_id": "task-safe-delivery",
    "correlation_id": "task-safe-correlation",
    "source_issue": "Young-Consultations/portfolio-tasks#42",
    "target_repository": "Young-Consultations/consulting-playbook",
}


class ReceiptJournal(AcceptingJournal):
    def __init__(self, effect=None):
        super().__init__()
        self.entries = [JournalComment(marker(ADMISSION, INPUT_BINDING), "router-bot")]
        if effect:
            record = {
                **INPUT_BINDING,
                "result_sha256": "a" * 64,
                "effect_class": effect,
                "effect_sha256": "b" * 64,
            }
            self.entries += [
                JournalComment(marker(RECEIPT, record), "receiver-bot"),
                JournalComment(marker(FORWARDED, record), "receiver-bot"),
            ]

    def comments(self, repository, issue):
        return list(self.entries)

    def trusted_author(self, author, role):
        return author == ("router-bot" if role == "admission" else "receiver-bot")


def run_bound_preflight(monkeypatch, journal):
    import json
    monkeypatch.setenv("SOURCE_ISSUE", INPUT_BINDING["source_issue"])
    monkeypatch.setenv("EXECUTION_INPUT_JSON", json.dumps(INPUT_BINDING))
    monkeypatch.setattr(preflight, "GitHubJournal", lambda: journal)
    return preflight.main()


def test_new_delivery_with_trusted_admission_has_no_prior_result(monkeypatch, tmp_path):
    journal = ReceiptJournal()
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert run_bound_preflight(monkeypatch, journal) == 0
    assert "prior_effect_class=none" in output.read_text()
    assert journal.forward_probes == ["Young-Consultations/portfolio-tasks"]


def test_terminal_failure_prevents_credential_dispatch_and_costly_work(monkeypatch, capsys):
    journal = ReceiptJournal("failed")
    assert run_bound_preflight(monkeypatch, journal) == 1
    assert journal.forward_probes == []
    assert "already has a terminal result" in capsys.readouterr().err


def test_nonmanaged_terminal_result_is_blocked(monkeypatch):
    for effect in ("rejected", "ambiguous-rejected", "verified", "blocked"):
        journal = ReceiptJournal(effect)
        assert run_bound_preflight(monkeypatch, journal) == 1
        assert not journal.forward_probes


def test_managed_draft_receipt_without_forwarding_can_recover_without_codex(monkeypatch, tmp_path):
    # Receiver's durable receipt can precede a failed source-forward call.
    # Returning managed-draft allows only the target's owned-PR reuse path.
    journal = ReceiptJournal("managed-draft")
    journal.entries.pop()  # no forwarded marker
    output = tmp_path / "result"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert run_bound_preflight(monkeypatch, journal) == 0
    assert "prior_effect_class=managed-draft" in output.read_text()
    assert journal.forward_probes == ["Young-Consultations/portfolio-tasks"]


def test_nonmanaged_terminal_receipt_without_forwarding_still_blocks(monkeypatch):
    for effect in ("failed", "rejected", "verified", "ambiguous-rejected"):
        journal = ReceiptJournal(effect)
        journal.entries.pop()
        assert run_bound_preflight(monkeypatch, journal) == 1
        assert journal.forward_probes == []


def test_receipt_only_managed_draft_requires_valid_binding_and_digest(monkeypatch):
    journal = ReceiptJournal("managed-draft")
    journal.entries.pop()
    receipt = {**INPUT_BINDING, "result_sha256": "not-a-digest",
               "effect_class": "managed-draft", "effect_sha256": "b" * 64}
    journal.entries[1] = JournalComment(marker(RECEIPT, receipt), "receiver-bot")
    assert run_bound_preflight(monkeypatch, journal) == 1


def test_managed_draft_is_only_permitted_for_owned_pr_reconciliation(monkeypatch, tmp_path):
    journal = ReceiptJournal("managed-draft")
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert run_bound_preflight(monkeypatch, journal) == 0
    assert "prior_effect_class=managed-draft" in output.read_text()


def test_untrusted_receipt_markers_are_ignored(monkeypatch):
    journal = ReceiptJournal()
    fake = {**INPUT_BINDING, "result_sha256": "a" * 64,
            "effect_class": "failed", "effect_sha256": "b" * 64}
    journal.entries.append(JournalComment(marker(RECEIPT, fake), "attacker"))
    assert run_bound_preflight(monkeypatch, journal) == 0


def test_duplicate_or_broken_journal_state_fails_closed(monkeypatch):
    journal = ReceiptJournal("managed-draft")
    journal.entries.append(journal.entries[1])
    assert run_bound_preflight(monkeypatch, journal) == 1

    journal = ReceiptJournal("managed-draft")
    journal.entries.pop(1)  # forwarded marker without its receipt
    assert run_bound_preflight(monkeypatch, journal) == 1

    journal = ReceiptJournal()
    journal.entries.clear()
    assert run_bound_preflight(monkeypatch, journal) == 1


def test_preflight_blocks_mismatched_terminal_binding(monkeypatch):
    journal = ReceiptJournal("managed-draft")
    record = {**INPUT_BINDING, "target_repository": "Young-Consultations/slugger",
              "result_sha256": "a" * 64, "effect_class": "managed-draft",
              "effect_sha256": "b" * 64}
    journal.entries[1] = JournalComment(marker(RECEIPT, record), "receiver-bot")
    assert run_bound_preflight(monkeypatch, journal) == 1


def test_preflight_rejects_malformed_bound_input(monkeypatch):
    journal = ReceiptJournal()
    monkeypatch.setenv("SOURCE_ISSUE", INPUT_BINDING["source_issue"])
    monkeypatch.setenv("EXECUTION_INPUT_JSON", "{")
    monkeypatch.setattr(preflight, "GitHubJournal", lambda: journal)
    assert preflight.main() == 1
    assert not journal.forward_probes


def test_malformed_trusted_terminal_markers_block_execution(monkeypatch):
    for prefix in (RECEIPT, FORWARDED):
        journal = ReceiptJournal()
        journal.entries.append(
            JournalComment(prefix + '{"delivery_id":"task-safe-delivery",} -->', "receiver-bot")
        )
        assert run_bound_preflight(monkeypatch, journal) == 1
        assert journal.forward_probes == []


def test_malformed_untrusted_terminal_markers_do_not_block(monkeypatch):
    journal = ReceiptJournal()
    journal.entries.append(
        JournalComment(RECEIPT + '{"delivery_id":"task-safe-delivery",} -->', "attacker")
    )
    assert run_bound_preflight(monkeypatch, journal) == 0


def test_recovered_managed_draft_has_distinct_canonical_digest(monkeypatch, tmp_path):
    journal = ReceiptJournal("managed-draft")
    record = {**INPUT_BINDING, "result_sha256": "c" * 64,
              "effect_class": "managed-draft", "effect_sha256": "b" * 64}
    journal.entries[2] = JournalComment(marker(FORWARDED, record), "receiver-bot")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    assert run_bound_preflight(monkeypatch, journal) == 0
    assert "prior_effect_class=managed-draft" in (tmp_path / "output").read_text()


def test_different_visible_effect_is_ambiguous(monkeypatch):
    journal = ReceiptJournal("managed-draft")
    record = {**INPUT_BINDING, "result_sha256": "c" * 64,
              "effect_class": "managed-draft", "effect_sha256": "d" * 64}
    journal.entries[2] = JournalComment(marker(FORWARDED, record), "receiver-bot")
    assert run_bound_preflight(monkeypatch, journal) == 1
