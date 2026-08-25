import json
import subprocess
from pathlib import Path

from scripts import validate_release

ROOT = Path(__file__).resolve().parents[1]


def test_current_release_candidate_is_structurally_coherent():
    assert validate_release.validate() == []


def test_unpublished_candidate_cannot_satisfy_publication_gate():
    errors = validate_release.validate(require_publishable=True)
    assert "publishable release must declare tag_published true" in errors


def test_mvp_fixture_targets_match_candidate_manifest():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    fixture = json.loads((ROOT / "tests/fixtures/mvp-v2/manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_version"] == "2.4.0"
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


def test_previous_known_good_is_published_2_3_2_commit():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["previous_known_good"] == {
        "release_version": "2.3.2",
        "commit_sha": "5738ace3ee90dde11336f8f8099e64e5645f7139",
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


def test_minor_candidate_preserves_published_2_3_2_as_history():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_version"] == "2.4.0"
    assert manifest["recovery_of"] == {
        "release_version": "2.3.2",
        "commit_sha": "5738ace3ee90dde11336f8f8099e64e5645f7139",
    }
