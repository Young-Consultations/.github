import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_default_branch_governance.py"
SPEC = importlib.util.spec_from_file_location("audit_default_branch_governance", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


POLICY = {
    "required_default_branch_ruleset": {
        "target": "branch",
        "enforcement": "active",
        "include_ref": "~DEFAULT_BRANCH",
        "require_no_bypass_actors": True,
        "required_rule_types": ["pull_request", "deletion", "non_fast_forward"],
        "pull_request": {"required_review_thread_resolution": True},
    }
}


def ruleset(*, enforcement="active", include=None, bypass=None, rule_types=None, thread_resolution=True):
    include = include or ["~DEFAULT_BRANCH"]
    bypass = bypass or []
    rule_types = rule_types or ["pull_request", "deletion", "non_fast_forward"]
    rules = []
    for rule_type in rule_types:
        rule = {"type": rule_type}
        if rule_type == "pull_request":
            rule["parameters"] = {
                "required_approving_review_count": 0,
                "dismiss_stale_reviews_on_push": False,
                "require_code_owner_review": False,
                "require_last_push_approval": False,
                "required_review_thread_resolution": thread_resolution,
                "allowed_merge_methods": ["merge", "squash", "rebase"],
            }
        rules.append(rule)
    return {
        "name": "Default branch change control",
        "target": "branch",
        "enforcement": enforcement,
        "conditions": {"ref_name": {"include": include, "exclude": []}},
        "rules": rules,
        "bypass_actors": bypass,
    }


def test_compliant_ruleset_passes():
    assert audit.evaluate_rulesets([ruleset()], POLICY) == []


def test_missing_ruleset_fails():
    errors = audit.evaluate_rulesets([], POLICY)
    assert errors == ["no active branch ruleset targets ~DEFAULT_BRANCH"]


def test_inactive_ruleset_fails():
    errors = audit.evaluate_rulesets([ruleset(enforcement="disabled")], POLICY)
    assert errors == ["no active branch ruleset targets ~DEFAULT_BRANCH"]


def test_wrong_ref_fails():
    errors = audit.evaluate_rulesets([ruleset(include=["refs/heads/release"])], POLICY)
    assert errors == ["no active branch ruleset targets ~DEFAULT_BRANCH"]


def test_missing_pull_request_rule_fails():
    errors = audit.evaluate_rulesets(
        [ruleset(rule_types=["deletion", "non_fast_forward"])],
        POLICY,
    )
    assert any("missing rule types: pull_request" in error for error in errors)


def test_bypass_actor_fails():
    errors = audit.evaluate_rulesets(
        [ruleset(bypass=[{"actor_id": 1, "actor_type": "RepositoryRole", "bypass_mode": "always"}])],
        POLICY,
    )
    assert any("bypass actors are configured" in error for error in errors)


def test_review_thread_resolution_is_required():
    errors = audit.evaluate_rulesets([ruleset(thread_resolution=False)], POLICY)
    assert any("does not require review-thread resolution" in error for error in errors)


def test_one_complete_ruleset_is_sufficient_even_with_other_partial_rulesets():
    partial = ruleset(rule_types=["deletion", "non_fast_forward"])
    assert audit.evaluate_rulesets([partial, ruleset()], POLICY) == []
