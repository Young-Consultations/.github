import base64
import json
import subprocess
import pytest
from pathlib import Path


from scripts import generate_current_runtime, runtime_preflight


@pytest.fixture(autouse=True)
def published_preflight_fixture(request, monkeypatch):
    # Keep deployed-mode regressions independent of the current candidate state.
    if request.node.name not in {
        "test_deployed_live_runtime_fails_before_cutover_and_accepts_exact_source_pin",
        "test_published_runtime_does_not_use_candidate_bypass",
        "test_missing_audit_token_reports_failed_credential_boundary",
    }:
        return
    original = runtime_preflight.load
    def load(path):
        value = original(path)
        if path == "release/current-runtime.json":
            value["release_state"] = "published"
            value["control_plane"].update(tag="ai-sdlc-v3.1.0", tag_published=True,
                tag_commit_sha="e9d11fc99fee73d247c93699f058ed64786bd4c0")
        return value
    monkeypatch.setattr(runtime_preflight, "load", load)


def test_current_runtime_record_is_generated_from_authoritative_state():
    path = Path("release/current-runtime.json")
    assert path.read_text(encoding="utf-8") == generate_current_runtime.render()
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["release_state"] == "candidate"
    assert value["control_plane"]["tag"] == "ai-sdlc-v4.0.0"
    assert value["control_plane"]["tag_published"] is False
    assert value["control_plane"]["tag_commit_sha"] is None
    assert value["activation"]["enabled_targets"] == [
        "Young-Consultations/consulting-playbook"
    ]


def test_attested_published_release_passes_offline_runtime_publication_gate():
    result = subprocess.run(
        ["python3", "scripts/runtime_preflight.py", "--offline", "--candidate"],
        check=False, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PASS"
    assert report["next_action"] == "run SIM"
    assert report["release_state"] == "candidate"
    assert report["checks"][1] == {
        "boundary": "release-publication", "status": "CANDIDATE",
    }




def _source_workflow(tag: str, *, extra_job: bool = False) -> dict:
    source = (
        "jobs:\n"
        + ("  unrelated:\n    uses: Young-Consultations/.github/"
           ".github/workflows/codex-router.yml@ai-sdlc-v3.1.0\n" if extra_job else "")
        + "  route:\n"
        + "    needs: prepare\n"
        + f"    uses: Young-Consultations/.github/.github/workflows/codex-router.yml@{tag}\n"
        + "  summary:\n    runs-on: ubuntu-latest\n"
    )
    return {
        "type": "file", "encoding": "base64",
        "content": base64.b64encode(source.encode("utf-8")).decode("ascii"),
    }


def test_source_router_pin_checks_exact_main_route_job(monkeypatch):
    expected_endpoint = (
        "repos/Young-Consultations/portfolio-tasks/contents/"
        ".github/workflows/route-approved-task.yml?ref=main"
    )

    def verified_api(endpoint, *, token=None):
        assert endpoint == expected_endpoint
        assert token == "audit-token"
        return _source_workflow("ai-sdlc-v3.1.0")

    monkeypatch.setattr(runtime_preflight, "api_one", verified_api)
    assert runtime_preflight.audit_source_router_pin("ai-sdlc-v3.1.0", "audit-token") == []


def test_source_router_pin_rejects_old_version_even_when_other_job_is_new(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight, "api_one",
        lambda *args, **kwargs: _source_workflow(
            "ai-sdlc-v3.0.3", extra_job=True,
        ),
    )
    errors = runtime_preflight.audit_source_router_pin(
        "ai-sdlc-v3.1.0", "audit-token"
    )
    assert len(errors) == 1
    assert errors[0].startswith("source-pin:")


def test_source_router_pin_fails_closed_on_inaccessible_or_invalid_evidence(monkeypatch):
    for value in (
        {"type": "file", "encoding": "base64", "content": "!invalid!"},
        {"type": "dir", "encoding": "base64", "content": "Z29vZA=="},
        _source_workflow("ai-sdlc-v3.1.0".replace("3.1.0", "main")),
    ):
        monkeypatch.setattr(runtime_preflight, "api_one", lambda *a, **k: value)
        # The mutable ref case must not be accepted; other malformed responses
        # also fail closed without silently treating missing evidence as PASS.
        assert runtime_preflight.audit_source_router_pin(
            "ai-sdlc-v3.1.0", "audit-token"
        )[0].startswith("source-pin:")
    monkeypatch.setattr(
        runtime_preflight, "api_one",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("not authorized")),
    )
    assert runtime_preflight.audit_source_router_pin(
        "ai-sdlc-v3.1.0", "audit-token"
    )[0].startswith("source-pin: cannot verify")


def test_deployed_live_runtime_fails_before_cutover_and_accepts_exact_source_pin(
    monkeypatch, capsys,
):
    monkeypatch.setenv("PREFLIGHT_AUDIT_TOKEN", "audit-token")
    monkeypatch.setattr(runtime_preflight, "remote_tag_commit",
                        lambda tag: "e9d11fc99fee73d247c93699f058ed64786bd4c0")
    monkeypatch.setattr(runtime_preflight, "audit_credentials", lambda *a: [])
    monkeypatch.setattr(runtime_preflight, "audit_result_sender_binding", lambda *a: [])
    monkeypatch.setattr("sys.argv", ["runtime_preflight.py"])
    monkeypatch.setattr(
        runtime_preflight, "api_one",
        lambda *a, **k: _source_workflow("ai-sdlc-v3.0.3"),
    )
    assert runtime_preflight.main() == 1
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["status"] == "FAIL"
    assert {"boundary": "deployed-source-router-pin", "status": "FAIL"} in rejected["checks"]
    assert any(x.startswith("source-pin:") for x in rejected["failures"])
    monkeypatch.setattr(
        runtime_preflight, "api_one",
        lambda *a, **k: _source_workflow("ai-sdlc-v3.1.0"),
    )
    assert runtime_preflight.main() == 0
    accepted = json.loads(capsys.readouterr().out)
    assert accepted["status"] == "PASS"
    assert {"boundary": "deployed-source-router-pin", "status": "PASS"} in accepted["checks"]


def test_published_runtime_does_not_use_candidate_bypass(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["runtime_preflight.py", "--offline", "--candidate"])
    assert runtime_preflight.main() != 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "FAIL"
    assert any("cannot use candidate mode" in x for x in report["failures"])


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
    manifest = json.loads(
        Path("release/release-manifest.json").read_text(encoding="utf-8")
    )
    monkeypatch.setattr(
        runtime_preflight,
        "remote_tag_commit",
        lambda tag: "e9d11fc99fee73d247c93699f058ed64786bd4c0",
    )
    # Exercise the published deployed mode. A missing audit token must
    # independently fail both credential metadata and source-pin verification.
    # Candidate mode is invalid for a published release and has its own test.
    monkeypatch.setattr("sys.argv", ["runtime_preflight.py"])

    assert runtime_preflight.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert {"boundary": "credential-metadata", "status": "FAIL"} in report["checks"]
    assert {"boundary": "deployed-source-router-pin", "status": "FAIL"} in report["checks"]
    assert report["failures"] == [
        "credentials: PREFLIGHT_AUDIT_TOKEN is unavailable",
        "source-pin: audit token unavailable",
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
