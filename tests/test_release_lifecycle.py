import json
import subprocess
from pathlib import Path

from scripts import validate_release

ROOT = Path(__file__).resolve().parents[1]


def test_current_release_candidate_is_structurally_coherent():
    assert validate_release.validate() == []


def test_patch_candidate_is_coherent_but_not_yet_publishable():
    assert validate_release.validate() == []
    assert validate_release.validate(require_publishable=True) == [
        "publishable release must declare tag_published true"
    ]


def test_mvp_fixture_targets_match_patch_candidate_manifest():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    fixture = json.loads((ROOT / "tests/fixtures/mvp-v2/manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_version"] == "2.4.1"
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


def test_previous_known_good_is_published_2_4_0_commit():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["previous_known_good"] == {
        "release_version": "2.4.0",
        "commit_sha": "42e8e0d3c888efbb3a21bd6762cb4fa416126529",
    }
    sha = manifest["previous_known_good"]["commit_sha"]
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
    assert manifest["tag_commit_sha"] is None


def test_manifest_paths_cannot_escape_the_repository(tmp_path):
    errors = []
    assert validate_release.safe_manifest_json_path(
        tmp_path, "../outside.json", "current_runtime", errors
    ) is None
    assert errors == ["current_runtime must be a safe repository-relative JSON path"]


def test_patch_candidate_preserves_published_2_4_0_as_history():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_version"] == "2.4.1"
    assert manifest["recovery_of"] is None
