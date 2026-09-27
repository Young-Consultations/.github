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
