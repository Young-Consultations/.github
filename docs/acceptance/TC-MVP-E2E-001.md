# TC-MVP-E2E-001: controlled end-to-end MVP acceptance

**Status:** Approved next-MVP acceptance design
**Owner:** `Young-Consultations/.github`
**Published baseline:** `ai-sdlc-v3.0.2` / `ai-sdlc-contract/v2`
**Current source-consumer pin:** `ai-sdlc-v3.0.2`
**Current live acceptance state:** REAL #154 proved the earlier initial path; REAL #156 exposed result-writer identity defect #83 during redelivery; REAL #159 exposed DEF-0073 at the receiver, which published 3.0.2 repaired. Deployed 3.0.2 Runtime Preflight and immutable REAL preflight passed, portfolio-tasks adopted 3.0.2, and #159 was reconciled while preserving its original trusted 3.0.1 admission. That recovery state exposed DEF-0086: published 3.0.2 cannot reuse the predecessor admission on unchanged authorized retry. Unpublished 3.0.3 plus immutable `codex-adapter-v3.0.3` is the current corrective candidate. #159 remains blocked until 3.0.3 publication, preflights, source repin, corrected terminal projection, and unchanged same-delivery redelivery complete
**Initial enabled target:** `Young-Consultations/consulting-playbook`

> **Historical 2.4.5 completion addendum:** REAL issue #151 exposed the 2.4.4 target publication-transport defect after successful Codex execution. The immutable repair is `codex-adapter-v2.4.5` (`4f062ca73acfc3458f0d690bf1c7687bafd0a8eb`) with conformance report SHA256 `8a7e3479a8768050b7621cec4d7663d8ab60d266291cb2d1027886200799c2fc`. Control-plane release `ai-sdlc-v2.4.5` resolves to `afe09d320268581bc83021cbfc80bf2a0f0bff91`; publication attestation merged, deployed Runtime Preflight run 36277959203 and immutable REAL preflight run 36278028013 passed, portfolio-tasks advanced to 2.4.5, and fresh issue #154 completed the live path through target run 36279165335 and managed draft PR #66. See [2.4.5 release procedure](../releases/2.4.5.md).

> **Historical 3.0.0 publication addendum:** REAL issue #156 reused the same managed draft without a second Codex execution but exposed #83: the deployed result writer could not authenticate its own durable receiver journal evidence. The corrected target is immutable `codex-adapter-v3.0.0` at `0fa11c078b248ea3201f0aa0f2912fce299a7766`, with conformance adapter revision `sha256:dc1c7706a6edfb430117999472c84defec27e498b91328c0090ea662b8209ab8` and report SHA256 `16333cad6ab38c0a799853a0ab32795525d026f98562982b697492f4b2f6ac91`. The published `ai-sdlc-v3.0.0` tag resolves to reviewed candidate merge commit `80889ca14b3bef4254d5212f7f801bf9877ddf72`. The 3.0.0 control plane binds result trust to `ai-sdlc-result-writer[bot]`, changes the required receiver secret from `CODEX_RESULT_TOKEN` to `RESULT_WRITER_PRIVATE_KEY`, and preserves payload `ai-sdlc-contract/v2`. Issue #85 established that this workflow-secret interface change is MAJOR. Publication does not yet mean live source adoption: portfolio-tasks remains on 2.4.5 until the sender allowlist, deployed preflights, and consumer pin are advanced. See [3.0.0 release procedure](../releases/3.0.0.md).

> **Historical 3.0.1 preflight-repair addendum:** Deployed 3.0.0 Runtime Preflight run
> 36370005352 passed activation, publication, and remote-tag boundaries and
> reported no source-sender mismatch, but falsely reported
> `AI_SDLC_RESULT_WRITER_PRIVATE_KEY` missing because the audit inspected only
> repository/environment secret metadata. The key is intentionally an
> organization Actions secret restricted to consulting-playbook. Published
> `ai-sdlc-v3.0.1` repairs only that metadata scope check and reuses immutable
> `codex-adapter-v3.0.0`. No new REAL execution is allowed until deployed 3.0.1 Runtime Preflight and immutable REAL preflight pass. See
> [3.0.1 release procedure](../releases/3.0.1.md).
>
> **Historical 3.0.2 receiver-compatibility addendum:** REAL #159 passed the dedicated
> result-writer token mint, App identity, and bounded delivery-prerequisite
> checks, then exposed DEF-0073 when the immutable 3.0.0 receiver forced the
> admission's `control_plane_release` to equal the receiver implementation
> release. Published `ai-sdlc-v3.0.2` replaces that accidental equality with
> an immutable receiver-owned compatibility allowlist. The enabled target is
> immutable `codex-adapter-v3.0.2` at
> `3bde0dc760088b9af21454a0f70ed498dae043a7`, pinning both credential
> preflight and receiver to 3.0.2. The policy explicitly accepts the existing
> 3.0.1 admission for #159 recovery and 3.0.2 admissions for new work after
> source cutover. Portfolio-tasks currently consumes 3.0.1. See
> [3.0.2 release procedure](../releases/3.0.2.md).
>
> **3.0.3 cross-release admission-reuse addendum:** After 3.0.2 publication,
> deployed preflights, source adoption, and successful #159 reconciliation,
> the source retained its original 3.0.1 admission but the 3.0.2 router would
> reject that binding as conflicting on unchanged retry. DEF-0086 resolves this
> by preserving exactly one trusted durable admission for the logical delivery.
> Exact same-release reuse remains unconditional; predecessor reuse is allowed
> only by immutable target-bound policy and must be accepted by the pinned
> receiver compatibility policy. The matching target is immutable
> `codex-adapter-v3.0.3` at
> `f11852c7f563df16ea4afa9ab75bf766242e7327`. See
> [3.0.3 release procedure](../releases/3.0.3.md).
>
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
3.0.2 receiver-compatibility and #159 recovery sequence defined in the current
addendum above.

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
6. pass target-produced results through the 3.0.3 control-plane receiver implementation with an in-memory journal/forwarding effect seam while preserving the immutable target adapter's reviewed 3.0.3 receiver pin and compatibility policy;
7. exercise successful implement behavior, managed-draft reuse, equivalent `draft-pr-created -> duplicate-reused` receiver no-op behavior, and conflicting duplicate-result rejection;
8. assert zero real Codex, branch, commit, push, PR, merge, release, deployment, production, or secret-output effects;
9. emit machine-readable release-comparison evidence for the 3.0.3 validation
   harness with `published_baseline: 3.0.2` and
   `candidate_release: 3.0.3`, record the exact `codex-adapter-v3.0.3`
   identity, keep `real_acceptance_satisfied: false`, and record that the
   3.0.3 control-plane tag is unpublished during candidate validation.

For retry evidence, `duplicate-reused` is accepted without another source projection only when it describes the same stable managed-draft effect as the prior successful result. A different branch, pull request, validation/test outcome, failure category, or any other non-approved result transition remains ambiguous and fails closed.

SIM may run on pull requests and by manual dispatch. It is deterministic compatibility evidence, not production-readiness evidence, and cannot substitute for the live acceptance run.

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

- `ai-sdlc-v3.0.3` has been reviewed, published, and attested on `main`;
- the published 2.4.4 tag remains unchanged as immutable historical evidence and is not treated as an execution-safe rollback for cost-bearing implementation;
- `consulting-playbook` is the sole enabled target;
- the registry identifies exact immutable `codex-adapter-v3.0.3` commit
  `f11852c7f563df16ea4afa9ab75bf766242e7327`, conformance adapter revision
  `sha256:3932def5d016b7db11869a0520087aeedcd092799e61dc8617be8bb2f020be3f`,
  and report SHA-256
  `a739cd3dde3c05121fbfc5360495880e265b76448b504936b8583b5efa972ec8`;
- fresh `TC-MVP-E2E-001-SIM` evidence passes and explicitly does not claim REAL acceptance;
- the selected task is harmless, deterministic, documentation-only where permitted, and within target policy;
- the intended publication boundary is draft-only;
- required source, router, target, publication, and receiver credentials have been human-reviewed and are available through their existing owners;
- `AI_SDLC_RESULT_WRITER_PRIVATE_KEY` is an organization Actions secret with `selected` visibility restricted to the enabled consulting target; Runtime Preflight proves that exact storage-scope binding without reading the value; the App is installed only on `portfolio-tasks`; and the immutable target invokes the reviewed 3.0.3 receiver interface, which accepts only `RESULT_WRITER_PRIVATE_KEY` to mint a fresh short-lived installation token;
- the result-delivery token authenticates as reviewed `ai-sdlc-result-writer[bot]`, distinct from every admission author; `portfolio-tasks` repository variable `PORTFOLIO_RESULT_SENDERS` exactly equals that immutable result-author allowlist; and the source reserves the credential-probe dispatch event for no-op capability verification.
- the 3.0.3 receiver compatibility policy is bound to the immutable receiver
  bundle and explicitly includes `ai-sdlc-v3.0.1`, `ai-sdlc-v3.0.2`, and
  `ai-sdlc-v3.0.3`; the consulting target's cross-release reuse set is the
  same reviewed set and target compatibility proves it is a subset of the
  receiver allowlist; unsupported release combinations remain fail-closed.

The organization REAL preflight itself performs no Codex invocation, branch creation, commit, push, PR creation, result forwarding, source mutation, merge, release, deployment, settings change, or production operation. After dispatch and before any cost-bearing Codex invocation, the selected target must run the control-plane-owned result-credential capability preflight. That bounded preflight creates and deletes one marker comment on the source issue to prove issue-write/cleanup access and GitHub-authored identity, then emits the dedicated no-op repository-dispatch event to prove forwarding access. No probe comment may remain afterward.

### Historical evidence and current 3.0.3 coordination

The earlier 2.4.5, 3.0.0, 3.0.1, and 3.0.2 sequences remain immutable evidence.

Published 3.0.2 repaired DEF-0073, passed deployed Runtime Preflight
36640642872 and immutable REAL preflight 36640734704, and was adopted by
portfolio-tasks. Source reconciliation run 36666315992 then cleared #159's
queued state while preserving its original trusted 3.0.1 admission and logical
delivery/correlation identity
`task-b72eaf2503fc3d27c82f8921e8cfbfff`.

That state exposed DEF-0086 before another Codex call: the 3.0.2 router would
regenerate current-release admission evidence and reject the preserved
predecessor admission.

Current sequence:

1. complete the 3.0.3 candidate and exact-head zero-effect gates;
2. merge the reviewed candidate and create immutable `ai-sdlc-v3.0.3` at the
   exact merge commit;
3. merge a separate publication-attestation PR;
4. run deployed 3.0.3 Runtime Preflight;
5. run immutable 3.0.3 REAL readiness preflight;
6. update portfolio-tasks from 3.0.2 to 3.0.3 through a reviewed source PR;
7. reauthorize the unchanged #159 issue without editing its body or replacing
   its 3.0.1 admission;
8. require one corrected terminal receiver/source projection through immutable
   `codex-adapter-v3.0.3`; and
9. reauthorize the unchanged delivery once more to prove `duplicate-reused`
   before Codex with no second branch, managed draft, receiver forwarding
   effect, or source projection.

Do not close #103 / DEF-0086, #100 / DEF-0073, or #83 / DEF-0064 until their
applicable REAL evidence is preserved.


### REAL execution procedure

After 3.0.3 publication attestation, deployed Runtime Preflight, immutable REAL
preflight, and portfolio source repin to 3.0.3 are green:

1. use existing portfolio issue #159 without modifying its body;
2. verify its single durable admission remains bound to
   `ai-sdlc-v3.0.1`, delivery/correlation
   `task-b72eaf2503fc3d27c82f8921e8cfbfff`, source
   `Young-Consultations/portfolio-tasks#159`, and target
   `Young-Consultations/consulting-playbook`;
3. an authorized human reapplies the unchanged approval action;
4. the 3.0.3 router proves exactly one trusted durable admission, reuses the
   predecessor admission through the target-bound compatibility policy, and
   dispatches immutable `codex-adapter-v3.0.3`;
5. the target independently revalidates caller, contract, target, task type,
   mode, deterministic branch ownership, draft-only policy, and all bounded
   cost-bearing prerequisites before Codex;
6. target execution, validation/tests, and managed draft publication complete,
   then the 3.0.3 receiver accepts the preserved 3.0.1 admission;
7. portfolio-tasks receives exactly one correlated terminal projection;
8. reapply the unchanged approval for the same logical delivery;
9. the target finds the existing managed draft and returns
   `duplicate-reused` before Codex; and
10. verify there is no second Codex execution, branch, managed draft, receiver
    forwarding effect, or source terminal projection.


### REAL evidence

The acceptance record must preserve links or immutable identities for:

- source issue and exact approved revision;
- task ID, delivery ID, attempt identity where available, and correlation ID;
- published corrective `ai-sdlc-v3.0.2` control-plane identity and its attested tag commit, plus immutable `codex-adapter-v3.0.2` and its reviewed 3.0.2 receiver pin;
- enabled target and registered immutable adapter commit;
- portfolio admission/router workflow run;
- target workflow run;
- managed draft PR;
- target validation/test status;
- canonical result/receiver evidence;
- source issue terminal projection proving the corrected #159 result reached the source exactly once;
- duplicate/redelivery evidence proving the unchanged logical delivery returns
  `duplicate-reused` before Codex and creates no second receiver/source effect;
- confirmation that no merge, release, deployment, settings, or production operation occurred.

Sensitive values and issue content not required for audit must be omitted or redacted.

## Acceptance decision

`TC-MVP-E2E-001-SIM` passes only when its deterministic compatibility evidence is green, the exact immutable target adapter and published receiver semantics were exercised, the equivalent retry produces no second visible effect, and every prohibited real-effect counter is zero.

`TC-MVP-E2E-001-REAL` passes only after 3.0.2 is published and attested,
deployed Runtime Preflight and immutable REAL preflight pass, portfolio-tasks
adopts 3.0.2, the unchanged #159 delivery produces one corrected terminal
projection through `codex-adapter-v3.0.2`, and unchanged same-delivery
redelivery returns `duplicate-reused` before Codex with no second visible
effect.

The MVP must not be reported accepted based on SIM, an unpublished candidate, REAL preflight, dispatch acknowledgement, or draft-PR creation alone.
