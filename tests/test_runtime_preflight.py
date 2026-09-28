import json
import subprocess
from pathlib import Path


from scripts import generate_current_runtime, runtime_preflight


def test_current_runtime_record_is_generated_from_authoritative_state():
    path = Path("release/current-runtime.json")
    assert path.read_text(encoding="utf-8") == generate_current_runtime.render()
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["release_state"] == "published"
    assert value["control_plane"]["tag"] == "ai-sdlc-v3.0.1"
    assert value["control_plane"]["tag_commit_sha"] == (
        "a98730deb729cc35dbd4d699395a87facb3ec78e"
    )
    assert value["activation"]["enabled_targets"] == [
        "Young-Consultations/consulting-playbook"
    ]


def test_offline_published_preflight_is_safe_and_passes_for_sim():
    result = subprocess.run(
        ["python3", "scripts/runtime_preflight.py", "--offline"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PASS"
    assert report["next_action"] == "run SIM"
    assert report["release_state"] == "published"
    assert report["checks"][1] == {
        "boundary": "release-publication",
        "status": "PASS",
    }


def test_credential_roles_cover_only_the_enabled_runtime_path():
    roles = json.loads(
        Path("config/codex-credential-roles.json").read_text(encoding="utf-8")
    )["repositories"]
    assert set(roles) == {
        "Young-Consultations/.github",
        "Young-Consultations/portfolio-tasks",
        "Young-Consultations/consulting-playbook",
    }
    assert "CODEX_ROUTER_TOKEN" in roles["Young-Consultations/portfolio-tasks"]["secrets"]
    assert "PORTFOLIO_APPROVERS" in roles["Young-Consultations/portfolio-tasks"]["variables"]
    consulting = roles["Young-Consultations/consulting-playbook"]
    assert "AI_SDLC_RESULT_WRITER_PRIVATE_KEY" in consulting["secrets"]
    assert "CODEX_RESULT_TOKEN" not in consulting["secrets"]
    assert "OPENAI_API_KEY" not in consulting["secrets"]
    assert "OPENAI_API_KEY" in (
        consulting["environments"]["consulting-playbook-codex"]["secrets"]
    )
    assert "Young-Consultations/slugger" not in roles


def test_workflow_separates_release_and_audit_credential_roles():
    workflow = Path(".github/workflows/runtime-preflight.yml").read_text(encoding="utf-8")
    assert "GH_TOKEN: ${{ github.token }}" in workflow
    assert "PREFLIGHT_AUDIT_TOKEN: ${{ secrets.PREFLIGHT_AUDIT_TOKEN }}" in workflow
    assert "GH_TOKEN: ${{ secrets.PREFLIGHT_AUDIT_TOKEN }}" not in workflow


def test_deployed_workflow_rejects_non_main_dispatch_before_checkout():
    import yaml

    workflow = yaml.safe_load(Path(".github/workflows/runtime-preflight.yml").read_text())
    steps = workflow["jobs"]["preflight"]["steps"]
    guard = steps[0]
    assert guard["if"] == "${{ !inputs.candidate_mode }}"
    assert "refs/heads/main" in guard["run"]
    assert "exit 1" in guard["run"]
    assert "actions/checkout@" in steps[1]["uses"]
    assert steps[1]["with"]["ref"] == "${{ inputs.candidate_mode && github.ref || 'main' }}"


def test_credential_metadata_uses_only_the_audit_token(monkeypatch):
    observed = {}

    def fake_api(endpoint, *, token=None):
        observed["endpoint"] = endpoint
        observed["token"] = token
        return [{"secrets": [{"name": "EXAMPLE"}]}]

    monkeypatch.setattr(runtime_preflight, "api", fake_api)
    assert runtime_preflight.named_values("org/repo", "secrets", "audit-token") == {
        "EXAMPLE"
    }
    assert observed == {
        "endpoint": "repos/org/repo/actions/secrets?per_page=100",
        "token": "audit-token",
    }


def test_selected_organization_secret_verifies_exact_repository(monkeypatch):
    observed = []

    def fake_api_one(endpoint, *, token=None):
        observed.append((endpoint, token))
        return {
            "name": "AI_SDLC_RESULT_WRITER_PRIVATE_KEY",
            "visibility": "selected",
        }

    def fake_api(endpoint, *, token=None):
        observed.append((endpoint, token))
        return [{
            "repositories": [
                {"full_name": "Young-Consultations/consulting-playbook"}
            ]
        }]

    monkeypatch.setattr(runtime_preflight, "api_one", fake_api_one)
    monkeypatch.setattr(runtime_preflight, "api", fake_api)
    assert runtime_preflight.organization_secret_selected_for_repository(
        "Young-Consultations/consulting-playbook",
        "AI_SDLC_RESULT_WRITER_PRIVATE_KEY",
        "audit-token",
    )
    assert observed == [
        (
            "orgs/Young-Consultations/actions/secrets/"
            "AI_SDLC_RESULT_WRITER_PRIVATE_KEY",
            "audit-token",
        ),
        (
            "orgs/Young-Consultations/actions/secrets/"
            "AI_SDLC_RESULT_WRITER_PRIVATE_KEY/repositories?per_page=100",
            "audit-token",
        ),
    ]


def test_selected_organization_secret_rejects_different_repository(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "api_one",
        lambda *args, **kwargs: {
            "name": "AI_SDLC_RESULT_WRITER_PRIVATE_KEY",
            "visibility": "selected",
        },
    )
    monkeypatch.setattr(
        runtime_preflight,
        "api",
        lambda *args, **kwargs: [{
            "repositories": [
                {"full_name": "Young-Consultations/another-repository"}
            ]
        }],
    )
    assert not runtime_preflight.organization_secret_selected_for_repository(
        "Young-Consultations/consulting-playbook",
        "AI_SDLC_RESULT_WRITER_PRIVATE_KEY",
        "audit-token",
    )


def test_broad_organization_secret_visibility_is_not_accepted(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "api_one",
        lambda *args, **kwargs: {
            "name": "AI_SDLC_RESULT_WRITER_PRIVATE_KEY",
            "visibility": "all",
        },
    )
    monkeypatch.setattr(
        runtime_preflight,
        "api",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("selected repository list must not be queried")
        ),
    )
    assert not runtime_preflight.organization_secret_selected_for_repository(
        "Young-Consultations/consulting-playbook",
        "AI_SDLC_RESULT_WRITER_PRIVATE_KEY",
        "audit-token",
    )


def test_repository_secret_role_accepts_selected_organization_secret(monkeypatch):
    roles = {
        "Young-Consultations/consulting-playbook": {
            "secrets": {
                "AI_SDLC_RESULT_WRITER_PRIVATE_KEY": "result writer private key"
            },
            "variables": {},
        }
    }

    def fake_named_values(repository, kind, audit_token, *, environment=None):
        assert repository == "Young-Consultations/consulting-playbook"
        assert audit_token == "audit-token"
        return set()

    monkeypatch.setattr(runtime_preflight, "named_values", fake_named_values)
    monkeypatch.setattr(
        runtime_preflight,
        "organization_secret_selected_for_repository",
        lambda repository, name, audit_token: True,
    )
    assert runtime_preflight.audit_credentials(roles, "audit-token") == []


def test_repository_secret_role_rejects_wrong_organization_selection(monkeypatch):
    roles = {
        "Young-Consultations/consulting-playbook": {
            "secrets": {
                "AI_SDLC_RESULT_WRITER_PRIVATE_KEY": "result writer private key"
            },
            "variables": {},
        }
    }
    monkeypatch.setattr(
        runtime_preflight,
        "named_values",
        lambda *args, **kwargs: set(),
    )
    monkeypatch.setattr(
        runtime_preflight,
        "organization_secret_selected_for_repository",
        lambda repository, name, audit_token: False,
    )
    assert runtime_preflight.audit_credentials(roles, "audit-token") == [
        "credentials: Young-Consultations/consulting-playbook secret "
        "AI_SDLC_RESULT_WRITER_PRIVATE_KEY is missing or is not an "
        "organization secret restricted to this repository"
    ]


def test_repository_secret_role_surfaces_org_metadata_audit_failure(monkeypatch):
    roles = {
        "Young-Consultations/consulting-playbook": {
            "secrets": {
                "AI_SDLC_RESULT_WRITER_PRIVATE_KEY": "result writer private key"
            },
            "variables": {},
        }
    }
    monkeypatch.setattr(
        runtime_preflight,
        "named_values",
        lambda *args, **kwargs: set(),
    )

    def unavailable(*args, **kwargs):
        raise subprocess.CalledProcessError(403, ["gh", "api"])

    monkeypatch.setattr(
        runtime_preflight,
        "organization_secret_selected_for_repository",
        unavailable,
    )
    failures = runtime_preflight.audit_credentials(roles, "audit-token")
    assert len(failures) == 1
    assert failures[0].startswith(
        "credentials: cannot verify Young-Consultations/consulting-playbook "
        "secret AI_SDLC_RESULT_WRITER_PRIVATE_KEY through organization scope:"
    )


def test_environment_credential_metadata_uses_environment_endpoint(monkeypatch):
    observed = {}

    def fake_api(endpoint, *, token=None):
        observed["endpoint"] = endpoint
        observed["token"] = token
        return [{"secrets": [{"name": "OPENAI_API_KEY"}]}]

    monkeypatch.setattr(runtime_preflight, "api", fake_api)
    assert runtime_preflight.named_values(
        "org/repo",
        "secrets",
        "audit-token",
        environment="consulting-playbook/codex",
    ) == {"OPENAI_API_KEY"}
    assert observed == {
        "endpoint": (
            "repos/org/repo/environments/consulting-playbook%2Fcodex/"
            "secrets?per_page=100"
        ),
        "token": "audit-token",
    }


def test_credential_audit_keeps_repository_and_environment_scopes_separate(
    monkeypatch,
):
    roles = {
        "org/repo": {
            "secrets": {"REPOSITORY_TOKEN": "repository role"},
            "variables": {},
            "environments": {
                "production": {
                    "secrets": {"OPENAI_API_KEY": "environment role"},
                    "variables": {"MODEL": "environment configuration"},
                }
            },
        }
    }
    values = {
        (None, "secrets"): {"REPOSITORY_TOKEN"},
        (None, "variables"): set(),
        ("production", "secrets"): {"OPENAI_API_KEY"},
        ("production", "variables"): {"MODEL"},
    }

    def fake_named_values(repository, kind, audit_token, *, environment=None):
        assert repository == "org/repo"
        assert audit_token == "audit-token"
        return values[(environment, kind)]

    monkeypatch.setattr(runtime_preflight, "named_values", fake_named_values)
    assert runtime_preflight.audit_credentials(roles, "audit-token") == []


def test_missing_environment_secret_identifies_exact_scope(monkeypatch):
    roles = {
        "org/repo": {
            "secrets": {},
            "variables": {},
            "environments": {
                "production": {
                    "secrets": {"OPENAI_API_KEY": "environment role"},
                    "variables": {},
                }
            },
        }
    }
    monkeypatch.setattr(runtime_preflight, "named_values", lambda *args, **kwargs: set())
    assert runtime_preflight.audit_credentials(roles, "audit-token") == [
        "credentials: org/repo environment production secret "
        "OPENAI_API_KEY is missing"
    ]


def test_repository_variable_value_uses_only_audit_token(monkeypatch):
    observed = {}

    def fake_api_one(endpoint, *, token=None):
        observed["endpoint"] = endpoint
        observed["token"] = token
        return {"name": "PORTFOLIO_RESULT_SENDERS", "value": "ai-sdlc-result-writer[bot]"}

    monkeypatch.setattr(runtime_preflight, "api_one", fake_api_one)
    assert runtime_preflight.repository_variable_value(
        "Young-Consultations/portfolio-tasks",
        "PORTFOLIO_RESULT_SENDERS",
        "audit-token",
    ) == "ai-sdlc-result-writer[bot]"
    assert observed == {
        "endpoint": (
            "repos/Young-Consultations/portfolio-tasks/actions/variables/"
            "PORTFOLIO_RESULT_SENDERS"
        ),
        "token": "audit-token",
    }


def test_result_sender_binding_requires_exact_trusted_result_author(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "repository_variable_value",
        lambda *args, **kwargs: "ai-sdlc-result-writer[bot]",
    )
    assert runtime_preflight.audit_result_sender_binding("audit-token") == []


def test_result_sender_binding_rejects_missing_trusted_result_author(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "repository_variable_value",
        lambda *args, **kwargs: "mightyjoe909",
    )
    assert runtime_preflight.audit_result_sender_binding("audit-token") == [
        "credentials: Young-Consultations/portfolio-tasks variable "
        "PORTFOLIO_RESULT_SENDERS must exactly match immutable "
        "trusted_result_authors"
    ]


def test_result_sender_binding_rejects_extra_sender(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "repository_variable_value",
        lambda *args, **kwargs: "ai-sdlc-result-writer[bot],mightyjoe909",
    )
    assert runtime_preflight.audit_result_sender_binding("audit-token") == [
        "credentials: Young-Consultations/portfolio-tasks variable "
        "PORTFOLIO_RESULT_SENDERS must exactly match immutable "
        "trusted_result_authors"
    ]


def test_missing_audit_token_reports_failed_credential_boundary(
    monkeypatch, capsys,
):
    monkeypatch.delenv("PREFLIGHT_AUDIT_TOKEN", raising=False)
    monkeypatch.setattr(
        runtime_preflight,
        "remote_tag_commit",
        lambda tag: "80889ca14b3bef4254d5212f7f801bf9877ddf72",
    )
    monkeypatch.setattr("sys.argv", ["runtime_preflight.py", "--candidate"])

    assert runtime_preflight.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["checks"][-1] == {
        "boundary": "credential-metadata",
        "status": "FAIL",
    }
    assert report["failures"] == [
        "credentials: PREFLIGHT_AUDIT_TOKEN is unavailable",
    ]


def test_remote_release_tag_resolves_lightweight_commit(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "api_one",
        lambda endpoint: {"object": {"type": "commit", "sha": "a" * 40}},
    )
    assert runtime_preflight.remote_tag_commit("ai-sdlc-v3.0.0") == "a" * 40


def test_remote_release_tag_resolves_annotated_tag(monkeypatch):
    values = iter([
        {"object": {"type": "tag", "sha": "b" * 40}},
        {"object": {"type": "commit", "sha": "c" * 40}},
    ])
    monkeypatch.setattr(runtime_preflight, "api_one", lambda endpoint: next(values))
    assert runtime_preflight.remote_tag_commit("ai-sdlc-v3.0.0") == "c" * 40
