import copy
import json
import subprocess

from tests.test_codex_router import BASE_TASK, output, run_router


class FakeTarget:
    def __init__(self):
        self.dispatch_attempts = 0
        self.accepted = set()
        self.executions = 0
        self.branches = {}
        self.prs = []
        self.results = []

    def deliver(self, execution, *, lost_ack=False):
        self.dispatch_attempts += 1
        delivery_id = execution["delivery_id"]
        branch = execution["requested_branch"]
        marker = f"<!-- ai-sdlc-delivery-id: {delivery_id} -->"
        matches = [pr for pr in self.prs if pr["marker"] == marker]
        if len(matches) > 1:
            return self._result(execution, "ambiguous-rejected", False)
        if matches:
            return self._result(execution, "duplicate-reused", False)
        if branch in self.branches and self.branches[branch] != delivery_id:
            return self._result(execution, "ambiguous-rejected", False)
        self.accepted.add(delivery_id)
        self.executions += 1
        self.branches[branch] = delivery_id
        self.prs.append({"branch": branch, "marker": marker, "draft": True})
        result = self._result(execution, "draft-pr-created", True)
        if lost_ack:
            raise RuntimeError("transport acknowledgement lost after accepted dispatch")
        return result

    def _result(self, execution, status, publication):
        result = {"delivery_id": execution["delivery_id"], "status": status, "publication": publication}
        self.results.append(result)
        return result

    def assert_invariant(self, delivery_id):
        assert sum(1 for owner in self.branches.values() if owner == delivery_id) <= 1
        assert sum(1 for pr in self.prs if f"ai-sdlc-delivery-id: {delivery_id}" in pr["marker"] and pr["draft"]) <= 1
        assert sum(1 for result in self.results if result["delivery_id"] == delivery_id and result["publication"]) <= 1


def canonical(**changes):
    result = run_router(**changes)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(output(result, "execution_input"))


def test_scenario_a_normal_delivery():
    target = FakeTarget(); execution = canonical()
    assert target.deliver(execution)["status"] == "draft-pr-created"
    assert target.dispatch_attempts == target.executions == len(target.branches) == len(target.prs) == 1
    target.assert_invariant(execution["delivery_id"])


def test_scenario_b_duplicate_before_first_completion_reuses_publication():
    target = FakeTarget(); first = canonical(); second = canonical()
    assert first["delivery_id"] == second["delivery_id"]
    assert target.deliver(first)["status"] == "draft-pr-created"
    assert target.deliver(second)["status"] == "duplicate-reused"
    assert target.dispatch_attempts == 2 and target.executions == 1 and len(target.prs) == 1
    target.assert_invariant(first["delivery_id"])


def test_scenario_c_lost_acknowledgement_redelivery_reuses_target_state():
    target = FakeTarget(); execution = canonical()
    try:
        target.deliver(execution, lost_ack=True)
    except RuntimeError:
        pass
    assert target.deliver(canonical())["status"] == "duplicate-reused"
    assert target.dispatch_attempts == 2 and target.executions == 1 and len(target.branches) == len(target.prs) == 1
    target.assert_invariant(execution["delivery_id"])


def test_scenario_d_later_redelivery_after_terminal_result_noops():
    target = FakeTarget(); execution = canonical()
    target.deliver(execution)
    assert target.deliver(canonical())["status"] == "duplicate-reused"
    assert target.executions == 1 and len(target.results) == 2
    target.assert_invariant(execution["delivery_id"])


def test_scenario_e_router_rejects_conflicting_payload_for_delivery_id(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.json"
    execution = canonical()
    monkeypatch.setenv("ROUTER_DELIVERY_LEDGER", str(ledger))
    monkeypatch.setenv("EXECUTION_INPUT", json.dumps(execution))
    monkeypatch.setenv("WORKFLOW_REF", "Young-Consultations/portfolio-tasks/.github/workflows/codex-execute.yml@codex-adapter-v2.3.2")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0))
    from scripts import codex_router
    repositories = codex_router.validate_registry()
    monkeypatch.setattr(codex_router, "routing_configuration", lambda: (
        repositories, {repository: True for repository in repositories}
    ))
    codex_router.dispatch()
    changed = copy.deepcopy(execution); changed["instructions"] = "Altered immutable instructions."
    monkeypatch.setenv("EXECUTION_INPUT", json.dumps(changed))
    try:
        codex_router.dispatch()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("conflict was not rejected")


def test_scenario_f_ambiguous_target_state_fails_closed():
    target = FakeTarget(); execution = canonical(); marker = f"<!-- ai-sdlc-delivery-id: {execution['delivery_id']} -->"
    target.prs.extend([{"branch": execution["requested_branch"], "marker": marker, "draft": True}, {"branch": execution["requested_branch"], "marker": marker, "draft": True}])
    assert target.deliver(execution)["status"] == "ambiguous-rejected"
    assert target.executions == 0
