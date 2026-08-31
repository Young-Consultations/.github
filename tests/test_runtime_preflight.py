import json
import subprocess
from pathlib import Path

from scripts import generate_current_runtime


def test_current_runtime_record_is_generated_from_authoritative_state():
    path = Path("release/current-runtime.json")
    assert path.read_text(encoding="utf-8") == generate_current_runtime.render()
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["release_state"] == "candidate"
    assert value["control_plane"]["tag"] == "ai-sdlc-v2.4.1"
    assert value["activation"]["enabled_targets"] == [
        "Young-Consultations/consulting-playbook"
    ]


def test_offline_candidate_preflight_is_safe_and_passes_for_sim():
    result = subprocess.run(
        ["python3", "scripts/runtime_preflight.py", "--offline", "--candidate"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PASS"
    assert report["next_action"] == "run SIM"


def test_deployed_preflight_fails_closed_while_release_is_candidate():
    result = subprocess.run(
        ["python3", "scripts/runtime_preflight.py", "--offline"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "FAIL"
    assert report["checks"][1] == {
        "boundary": "release-publication",
        "status": "FAIL",
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
