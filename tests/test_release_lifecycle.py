import json
import subprocess
from pathlib import Path

from scripts import validate_release

ROOT = Path(__file__).resolve().parents[1]


def test_current_release_is_coherent_and_immutable():
    assert validate_release.validate() == []


def test_recovery_candidate_is_explicitly_not_publishable_yet():
    errors = validate_release.validate(require_publishable=True)
    assert "publishable release must declare tag_published true" in errors
    assert "publishable release must name at least one trusted journal author" in errors
    for repository in (
        "Young-Consultations/.github",
        "Young-Consultations/consulting-playbook",
        "Young-Consultations/portfolio-tasks",
        "Young-Consultations/slugger",
    ):
        assert any(error.startswith(f"{repository}: reviewed conformance evidence") for error in errors)
        assert any(error.startswith(f"{repository}: publishable release requires") for error in errors)


def test_mvp_fixture_uses_current_release_identity_and_targets():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    fixture = json.loads((ROOT / "tests/fixtures/mvp-v2/manifest.json").read_text(encoding="utf-8"))
    assert manifest["tag_published"] is False
    assert "immutable_reference" not in fixture
    assert "immutable_reference" not in manifest
    assert sorted(fixture["targets"]) == manifest["supported_targets"]


def test_mutable_router_reference_is_rejected(tmp_path):
    for path in (
        "release/release-manifest.json", "contracts/contract-version.txt",
        "config/codex-repositories.json", "config/codex-activation.json",
        "pyproject.toml", "README.md",
    ):
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / path).read_bytes())
    workflow = tmp_path / ".github/workflows/caller.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "uses: Young-Consultations/.github/.github/workflows/codex-router.yml@main\n",
        encoding="utf-8",
    )
    assert any("mutable organization workflow ref" in error for error in validate_release.validate(tmp_path))


def test_previous_known_good_is_a_restorable_commit():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    sha = manifest["previous_known_good"]["commit_sha"]
    assert len(sha) == 40
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_candidate_does_not_embed_its_own_future_commit_identity():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    assert "immutable_reference" not in manifest


def test_patch_candidate_preserves_the_broken_baseline_as_history():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_version"] == "2.3.1"
    assert manifest["recovery_of"] == {
        "release_version": "2.3.0",
        "commit_sha": "c6090e5bbadcc2102a1cb91875466e9decdada1e",
    }
