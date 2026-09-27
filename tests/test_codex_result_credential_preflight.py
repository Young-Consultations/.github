from scripts import codex_result_credential_preflight as preflight


class AcceptingJournal:
    def __init__(self):
        self.repositories = []

    def authenticate(self, repository):
        self.repositories.append(repository)


class RejectingJournal:
    def authenticate(self, repository):
        raise preflight.ReceiverError(
            "authentication",
            "result credential principal is not an approved result journal author",
        )


def test_preflight_accepts_trusted_result_writer_and_source_access(monkeypatch):
    journal = AcceptingJournal()
    monkeypatch.setenv("SOURCE_REPOSITORY", "Young-Consultations/portfolio-tasks")
    monkeypatch.setattr(preflight, "GitHubJournal", lambda: journal)

    assert preflight.main() == 0
    assert journal.repositories == ["Young-Consultations/portfolio-tasks"]


def test_preflight_fails_closed_on_untrusted_result_writer(monkeypatch):
    monkeypatch.setenv("SOURCE_REPOSITORY", "Young-Consultations/portfolio-tasks")
    monkeypatch.setattr(preflight, "GitHubJournal", RejectingJournal)

    assert preflight.main() == 1


def test_preflight_rejects_malformed_source_without_authentication(monkeypatch):
    monkeypatch.setenv("SOURCE_REPOSITORY", "not a repository")
    monkeypatch.setattr(
        preflight,
        "GitHubJournal",
        lambda: (_ for _ in ()).throw(AssertionError("must not authenticate")),
    )

    assert preflight.main() == 1
