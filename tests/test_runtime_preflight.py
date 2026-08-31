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
