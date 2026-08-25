# TC-MVP-E2E-001: controlled end-to-end MVP acceptance

**Status:** Approved next-MVP acceptance design  
**Owner:** `Young-Consultations/.github`  
**Applies to:** `ai-sdlc-v2.3.2` / `ai-sdlc-contract/v2`  
**Initial enabled target:** `Young-Consultations/consulting-playbook`

## Purpose

`TC-MVP-E2E-001` proves the approved-portfolio-issue-to-correlated-draft-PR path without creating a second orchestration engine. It has two modes that share the same contract identities, admission semantics, target boundary, result semantics, receiver rules, source projection, and idempotency expectations.

The modes differ only at explicit effect/provider boundaries:

- `TC-MVP-E2E-001-SIM` replaces Codex and publication effects with deterministic fakes and is safe for repeatable CI.
- `TC-MVP-E2E-001-REAL` uses the deployed source, router, target, Codex, draft-publication, receiver, and source-projection path under an explicit human gate.

Passing SIM is required before REAL, but SIM never satisfies REAL acceptance or MVP completion.

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
6. exercise successful implement behavior, managed-draft reuse, duplicate delivery, receiver idempotency, and conflicting duplicate-result rejection;
7. assert zero real Codex, branch, commit, push, PR, merge, release, deployment, production, or secret-output effects;
8. emit machine-readable evidence that explicitly records `real_acceptance_satisfied: false`.

SIM may run on pull requests and by manual dispatch. It is not production-readiness evidence and cannot substitute for the live acceptance run.

## TC-MVP-E2E-001-REAL

REAL proves the deployed integration that SIM cannot prove, including human approval provenance, GitHub event routing, credentials, real Codex execution, real target validation, draft publication, receiver delivery, and source projection.

### Human gate and trigger ownership

REAL must **not** be initiated by a control-plane workflow that fabricates or applies source approval. `portfolio-tasks/.github/workflows/route-approved-task.yml` requires the `status:approved` label event to be performed by an authorized human and rejects bot actors. That source-owned gate is part of the acceptance evidence, not an inconvenience to route around.

Therefore the REAL acceptance mechanism is intentionally split into:

1. a non-mutating `.github` REAL preflight;
2. the existing human-owned `portfolio-tasks` approval action, which triggers the canonical production-shaped route;
3. post-run evidence review of the existing router, target, receiver, source projection, and managed draft PR.

No alternate control-plane dispatch path is permitted.

### REAL preflight

Before the human approval action, the acceptance workflow shall fail closed unless:

- the published compatibility release is exactly `ai-sdlc-v2.3.2`;
- `consulting-playbook` is the sole enabled target;
- the registry identifies the exact immutable adapter commit used by SIM and REAL;
- fresh `TC-MVP-E2E-001-SIM` evidence passes and explicitly does not claim REAL acceptance;
- the selected task is harmless, deterministic, documentation-only where permitted, and within target policy;
- the intended publication boundary is draft-only;
- required source, router, target, publication, and receiver credentials have been human-reviewed and are available through their existing owners.

The preflight itself performs no Codex invocation, branch creation, commit, push, PR creation, result forwarding, source mutation, merge, release, deployment, settings change, or production operation.

### REAL execution procedure

After PR #54 is merged and the preflight is green:

1. Create or select one harmless `portfolio-tasks` issue targeting `Young-Consultations/consulting-playbook`, with explicit `implement` mode and the current canonical task fields.
2. Review the exact executable issue revision and confirm no material edit remains pending.
3. An authorized human applies `status:approved`. This is the REAL execution trigger.
4. The existing portfolio source workflow constructs the canonical approved task and invokes the published `ai-sdlc-v2.3.2` router.
5. The router validates current registration and activation, constructs stable task/delivery/correlation identities, and dispatches the immutable registered target workflow.
6. The `consulting-playbook` target independently validates caller, contract, target identity, task type, mode, deterministic branch ownership, and draft-only policy before Codex.
7. Real Codex executes only inside the selected target repository.
8. Target validation/tests pass before publication.
9. The target creates exactly one managed draft PR or reuses the existing owned draft for the delivery.
10. The target returns one canonical `execution-result/v2` through the organization receiver.
11. `portfolio-tasks` shows the correlated terminal result, validation status, and draft-PR link.
12. Re-run/redelivery of the same approved delivery is used to verify no second visible implementation effect is created.

### REAL evidence

The acceptance record must preserve links or immutable identities for:

- source issue and exact approved revision;
- task ID, delivery ID, attempt identity where available, and correlation ID;
- `ai-sdlc-v2.3.2` release identity;
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

`TC-MVP-E2E-001-SIM` passes only when its deterministic evidence is green and every prohibited real-effect counter is zero.

`TC-MVP-E2E-001-REAL` passes only after the deliberate human-triggered live run completes with one correlated managed draft PR, one canonical result, correct source projection, and successful retry/idempotency evidence.

The MVP must not be reported accepted based on SIM, REAL preflight, dispatch acknowledgement, or draft-PR creation alone.
