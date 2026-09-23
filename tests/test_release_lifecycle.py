import json
import subprocess
from pathlib import Path

from scripts import validate_release

ROOT = Path(__file__).resolve().parents[1]


def test_current_published_release_is_structurally_coherent():
    assert validate_release.validate() == []


def test_published_release_passes_publication_gate():
    assert validate_release.validate() == []
    assert validate_release.validate(require_publishable=True) == []
    assert validate_release.validate(require_candidate_ready=True) == [
        "candidate readiness requires an unpublished release without a tag commit"
    ]


def test_published_release_requires_trusted_journal_authors(monkeypatch):
    original_load = validate_release.load_json

    def without_result_authors(path):
        document = original_load(path)
        if path.name == "codex-result-trust.json":
            document["trusted_result_authors"] = []
        return document

    monkeypatch.setattr(validate_release, "load_json", without_result_authors)
    assert "release readiness must name trusted authors for every journal role" in (
        validate_release.validate(require_publishable=True)
    )


def test_mvp_fixture_targets_match_published_manifest():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    fixture = json.loads((ROOT / "tests/fixtures/mvp-v2/manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_version"] == "2.4.4"
    assert manifest["tag_published"] is True
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


def test_previous_known_good_is_published_2_4_3_commit():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["previous_known_good"] == {
        "release_version": "2.4.3",
        "commit_sha": "3da7ed9b7bf76d00ae35e4accc733ac8f95259c5",
    }
    sha = manifest["previous_known_good"]["commit_sha"]
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_published_tag_resolves_to_attested_merge_commit():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    assert "immutable_reference" not in manifest
    assert manifest["tag_commit_sha"] == "adb57508762168b3410f52e8a7b0151078c6e9b9"
    result = subprocess.run(
        ["git", "rev-list", "-n", "1", manifest["tag"]],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == manifest["tag_commit_sha"]


def test_manifest_paths_cannot_escape_the_repository(tmp_path):
    errors = []
    assert validate_release.safe_manifest_json_path(
        tmp_path, "../outside.json", "current_runtime", errors
    ) is None
    assert errors == ["current_runtime must be a safe repository-relative JSON path"]


def test_patch_release_preserves_published_2_4_3_as_history():
    manifest = json.loads((ROOT / "release/release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_version"] == "2.4.4"
    assert manifest["previous_known_good"]["release_version"] == "2.4.3"
    assert manifest["recovery_of"] is None
