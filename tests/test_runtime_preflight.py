import json
import subprocess
from pathlib import Path

from scripts import generate_current_runtime, runtime_preflight


def test_current_runtime_record_is_generated_from_authoritative_state():
    path = Path("release/current-runtime.json")
    assert path.read_text(encoding="utf-8") == generate_current_runtime.render()
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["release_state"] == "published"
    assert value["control_plane"]["tag"] == "ai-sdlc-v2.4.1"
    assert value["control_plane"]["tag_commit_sha"] == "34ec7dc1cf54f960757781851384e0f6b15f7b63"
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
    assert "OPENAI_API_KEY" in roles["Young-Consultations/consulting-playbook"]["secrets"]
    assert "Young-Consultations/slugger" not in roles


def test_workflow_separates_release_and_audit_credential_roles():
    workflow = Path(".github/workflows/runtime-preflight.yml").read_text(encoding="utf-8")
    assert "GH_TOKEN: ${{ github.token }}" in workflow
    assert "PREFLIGHT_AUDIT_TOKEN: ${{ secrets.PREFLIGHT_AUDIT_TOKEN }}" in workflow
    assert "GH_TOKEN: ${{ secrets.PREFLIGHT_AUDIT_TOKEN }}" not in workflow


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


def test_missing_audit_token_reports_failed_credential_boundary(
    monkeypatch, capsys,
):
    expected_commit = "34ec7dc1cf54f960757781851384e0f6b15f7b63"
    monkeypatch.delenv("PREFLIGHT_AUDIT_TOKEN", raising=False)
    monkeypatch.setattr(runtime_preflight, "remote_tag_commit", lambda tag: expected_commit)
    monkeypatch.setattr("sys.argv", ["runtime_preflight.py"])

    assert runtime_preflight.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["checks"][-1] == {
        "boundary": "credential-metadata",
        "status": "FAIL",
    }
    assert report["failures"] == [
        "credentials: PREFLIGHT_AUDIT_TOKEN is unavailable"
    ]


def test_remote_release_tag_resolves_lightweight_commit(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "api_one",
        lambda endpoint: {"object": {"type": "commit", "sha": "a" * 40}},
    )
    assert runtime_preflight.remote_tag_commit("ai-sdlc-v2.4.1") == "a" * 40


def test_remote_release_tag_resolves_annotated_tag(monkeypatch):
    values = iter([
        {"object": {"type": "tag", "sha": "b" * 40}},
        {"object": {"type": "commit", "sha": "c" * 40}},
    ])
    monkeypatch.setattr(runtime_preflight, "api_one", lambda endpoint: next(values))
    assert runtime_preflight.remote_tag_commit("ai-sdlc-v2.4.1") == "c" * 40
