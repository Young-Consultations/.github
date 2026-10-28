from unittest.mock import patch
import pytest
from scripts import verify_target_workflows as checker

REF = "ai-sdlc-v2.3.2"
SHA = "5738ace3ee90dde11336f8f8099e64e5645f7139"


def test_frozen_receiver_checks_every_dependency_at_exact_commit():
    hashes = iter(["84e0f54967554b4425841d9057c5cd520e866032",
                   "f765135b1f7b88b43e83625999ea4d085dc86bc1",
                   "9803dc3dfe46f6201d01402e322e3b385f900f80",
                   "69385cb554e248545f967d094108fbd1ce8b8573",
                   "02ba5fd11b6903f50eccc283679c0b5ac85c4714"])
    with patch.object(checker, "fetch_ref_commit", return_value=SHA), \
         patch.object(checker, "fetch_content", return_value=b"fixture") as fetch, \
         patch.object(checker, "git_blob_sha1", side_effect=lambda _: next(hashes)):
        assert checker.verify_receiver_at_ref(REF, None, set(), allow_disabled_legacy=True) == "CODEX_RESULT_TOKEN"
        assert fetch.call_count == 5
        assert all(call.args[2] == SHA for call in fetch.call_args_list)


@pytest.mark.parametrize("commit,reuse", [("f" * 40, set()), (SHA, {"ai-sdlc-v4.0.0"})])
def test_historical_receiver_rejects_changed_identity_or_cross_release_reuse(commit, reuse):
    with patch.object(checker, "fetch_ref_commit", return_value=commit), \
         patch.object(checker, "fetch_content") as fetch:
        with pytest.raises(checker.CompatibilityError):
            checker.verify_receiver_at_ref(REF, None, reuse, allow_disabled_legacy=True)
        fetch.assert_not_called()


def test_historical_receiver_rejects_changed_bytes():
    with patch.object(checker, "fetch_ref_commit", return_value=SHA), \
         patch.object(checker, "fetch_content", return_value=b"tampered"):
        with pytest.raises(checker.CompatibilityError, match="bytes changed"):
            checker.verify_receiver_at_ref(REF, None, set(), allow_disabled_legacy=True)


def test_enabled_historical_receiver_still_uses_current_semantic_checks():
    with patch.object(checker, "fetch_ref_commit", return_value=SHA), \
         patch.object(checker, "fetch_workflow", return_value="bad historical workflow"), \
         patch.object(checker, "fetch_content") as fetch:
        with pytest.raises(checker.CompatibilityError):
            checker.verify_receiver_at_ref(REF, None)
        fetch.assert_not_called()
