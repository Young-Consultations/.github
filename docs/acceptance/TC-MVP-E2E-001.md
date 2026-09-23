# TC-MVP-E2E-001: controlled end-to-end MVP acceptance

**Status:** Approved next-MVP acceptance design
**Owner:** `Young-Consultations/.github`
**Published baseline:** `ai-sdlc-v2.4.3` / `ai-sdlc-contract/v2`
**Current corrective release required for the next REAL run:** `ai-sdlc-v2.4.4`
**Initial enabled target:** `Young-Consultations/consulting-playbook`

> **2.4.4 candidate addendum:** The immutable target repair is tagged at `codex-adapter-v2.4.4` (`70ea4342abf7115f6848ea32bb958bbf6be696c1`). The control-plane 2.4.4 candidate is unpublished. The 2.4.3 release remains published and is the previous known good baseline. The next REAL gate requires 2.4.4 publication attestation, deployed Runtime Preflight, immutable REAL preflight, and a fresh human-approved issue. See [2.4.4 release procedure](../releases/2.4.4.md). The historical 2.4.3 sequence below records the prior repair.

## Purpose

> **Historical 2.4.3 operating addendum:** At that stage, the 2.4.2 repair release was the published
> rollback baseline. The planned REAL gate required 2.4.3 and
> additionally requires one-action approval, the self-pinned router bundle, one
> activation snapshot, router-owned admission, complete comment pagination,
> the generated current-runtime record, and a passing deployed Runtime
> Preflight. The state sequence remains `PROPOSED -> APPROVED -> ADMITTED ->
> DISPATCHED -> TARGET_TERMINAL -> RECEIVED -> PROJECTED`; rejection,
> reconciliation, and quarantine remain fail-closed outcomes.

`TC-MVP-E2E-001` proves the approved-portfolio-issue-to-correlated-draft-PR path without creating a second orchestration engine. It has two modes that share the same contract identities, admission semantics, target boundary, result semantics, receiver rules, source projection, and idempotency expectations.

The modes differ only at explicit effect/provider boundaries:

- `TC-MVP-E2E-001-SIM` replaces Codex and publication effects with deterministic fakes and is safe for repeatable CI.
- `TC-MVP-E2E-001-REAL` uses the deployed source, router, target, Codex, draft-publication, receiver, and source-projection path under an explicit human gate.

Passing SIM is required before REAL, but SIM never satisfies REAL acceptance or MVP completion.

## Historical compatibility correction

The published `ai-sdlc-v2.3.2` unit remains immutable. While replacing a simplified SIM receiver with the actual receiver implementation, DEF-0032 exposed a retry contradiction: a correct target returns `draft-pr-created` on the first successful delivery and `duplicate-reused` when the same managed draft is discovered on redelivery, while the published receiver rejected every non-identical second result for a delivery.

The approved correction preserves both intended rules by distinguishing canonical-result identity from stable visible-effect identity. `draft-pr-created -> duplicate-reused` is accepted as an idempotent no-op only when it represents the same delivery, target, correlation, managed branch/PR, validation result, test result, and failure category. Every other non-identical result remains ambiguous and fails closed.

This correction was introduced through PR #54 and published in
`ai-sdlc-v2.4.0`. The history explains why SIM exercises the receiver's
redelivery behavior; it is not the current release gate. The active gate is the
2.4.4 target-repair sequence defined in the current addendum above.

## Shared architecture

Both modes preserve this logical path:

`portfolio task -> revision-bound human approval -> canonical task -> organization router -> target-owned adapter -> execution provider -> target validation -> draft publication/result -> organization receiver -> portfolio result projection`

The control plane must not impersonate a target or bypass source approval. In particular, the enabled `consulting-playbook` adapter independently enforces `Young-Consultations/consulting-playbook` as its target identity.

## TC-MVP-E2E-001-SIM

SIM is deterministic evidence for the shared target/result semantics without paid Codex or uncontrolled GitHub mutation.

The SIM harness shall:

1. resolve the sole enabled target from the current activation state;
2. resolve that target's immutable adapter commit from the current registry;
3. run the exact target-owned adapter from that immutable commit;
4. inject deterministic fake Codex and publication effects at the target's existing effect/provider seam;
5. preserve canonical `execution-input/v2` and `execution-result/v2` semantics;
6. pass target-produced results through the candidate organization receiver implementation with an in-memory journal/forwarding effect seam;
7. exercise successful implement behavior, managed-draft reuse, equivalent `draft-pr-created -> duplicate-reused` receiver no-op behavior, and conflicting duplicate-result rejection;
8. assert zero real Codex, branch, commit, push, PR, merge, release, deployment, production, or secret-output effects;
9. emit machine-readable evidence that records published baseline 2.4.3,
   corrective candidate 2.4.4, exact target adapter identity,
   `real_acceptance_satisfied: false`, and whether the candidate tag is
   published.

For retry evidence, `duplicate-reused` is accepted without another source projection only when it describes the same stable managed-draft effect as the prior successful result. A different branch, pull request, validation/test outcome, failure category, or any other non-approved result transition remains ambiguous and fails closed.

SIM may run on pull requests and by manual dispatch. It is candidate evidence, not production-readiness evidence, and cannot substitute for the live acceptance run.

## TC-MVP-E2E-001-REAL

REAL proves the deployed integration that SIM cannot prove, including human approval provenance, GitHub event routing, credentials, real Codex execution, real target validation, draft publication, receiver delivery, source projection, and redelivery behavior.

### Human gate and trigger ownership

REAL must **not** be initiated by a control-plane workflow that fabricates or applies source approval. `portfolio-tasks/.github/workflows/route-approved-task.yml` requires the `status:approved` label event to be performed by an authorized human and rejects bot actors. That source-owned gate is part of the acceptance evidence, not an inconvenience to route around.

Therefore the REAL acceptance mechanism is intentionally split into:

1. a non-mutating `.github` REAL preflight;
2. the existing human-owned `portfolio-tasks` approval action, which triggers the canonical production-shaped route;
3. post-run evidence review of the existing router, target, receiver, source projection, and managed draft PR.

No alternate control-plane dispatch path is permitted.

### REAL preflight

Before the human approval action, the acceptance workflow shall fail closed unless:

- `ai-sdlc-v2.4.4` has been reviewed, published, and attested on `main`;
- the published 2.4.3 tag remains unchanged as rollback evidence;
- `consulting-playbook` is the sole enabled target;
- the registry identifies exact immutable `codex-adapter-v2.4.4` commit and
  report-digest evidence, and the adapter remains receiver-compatible;
- fresh `TC-MVP-E2E-001-SIM` evidence passes and explicitly does not claim REAL acceptance;
- the selected task is harmless, deterministic, documentation-only where permitted, and within target policy;
- the intended publication boundary is draft-only;
- required source, router, target, publication, and receiver credentials have been human-reviewed and are available through their existing owners.

The preflight itself performs no Codex invocation, branch creation, commit, push, PR creation, result forwarding, source mutation, merge, release, deployment, settings change, or production operation.

### Release/target coordination before REAL

The target repair is published as `codex-adapter-v2.4.4`, while the
control-plane candidate remains unpublished. The source consumer still selects
2.4.3. Before REAL:

1. merge the reviewed 2.4.4 control-plane candidate, tag its exact merge commit,
   and attest that identity in a separate merged PR;
2. run deployed Runtime Preflight with `candidate_mode: false`;
3. run REAL preflight from the attested `main` checkout;
4. require both gates to pass before approving a fresh harmless live test issue;
5. update the source consumer to the published 2.4.4 router after review and gates.

### REAL execution procedure

After the corrective release and target pin are published and REAL preflight is green:

1. Create or select one harmless `portfolio-tasks` issue targeting `Young-Consultations/consulting-playbook`, with explicit `implement` mode and the current canonical task fields.
2. Review the exact executable issue revision and confirm no material edit remains pending.
3. An authorized human applies `status:approved`. This is the REAL execution trigger.
4. The existing portfolio source workflow constructs the canonical approved task and invokes the published corrective router release.
5. The router validates current registration and activation, constructs stable task/delivery/correlation identities, and dispatches the immutable registered target workflow.
6. The `consulting-playbook` target independently validates caller, contract, target identity, task type, mode, deterministic branch ownership, and draft-only policy before Codex.
7. Real Codex executes only inside the selected target repository.
8. Target validation/tests pass before publication.
9. The target creates exactly one managed draft PR or reuses the existing owned draft for the delivery.
10. The target returns one canonical `execution-result/v2` through the
    published 2.4.4 organization receiver.
11. `portfolio-tasks` shows the correlated terminal result, validation status, and draft-PR link.
12. Re-run/redelivery of the same approved delivery verifies that the target returns `duplicate-reused` for the same managed draft, the receiver accepts that equivalent visible effect as a no-op, and no second source projection or draft PR is created.

### REAL evidence

The acceptance record must preserve links or immutable identities for:

- source issue and exact approved revision;
- task ID, delivery ID, attempt identity where available, and correlation ID;
- published `ai-sdlc-v2.4.4` release identity and its attested tag commit;
- enabled target and registered immutable adapter commit;
- portfolio admission/router workflow run;
- target workflow run;
- managed draft PR;
- target validation/test status;
- canonical result/receiver evidence;
- source issue terminal projection;
- duplicate/redelivery evidence;
- confirmation that no merge, release, deployment, settings, or production operation occurred.

Sensitive values and issue content not required for audit must be omitted or redacted.

## Acceptance decision

`TC-MVP-E2E-001-SIM` passes only when its deterministic candidate evidence is green, the exact immutable target adapter and candidate receiver semantics were exercised, the equivalent retry produces no second visible effect, and every prohibited real-effect counter is zero.

`TC-MVP-E2E-001-REAL` passes only after the corrective receiver is in a published immutable compatibility release, the selected target is immutably pinned to it, and the deliberate human-triggered live run completes with one correlated managed draft PR, one canonical source projection, and successful equivalent retry/idempotency evidence.

The MVP must not be reported accepted based on SIM, an unpublished candidate, REAL preflight, dispatch acknowledgement, or draft-PR creation alone.
