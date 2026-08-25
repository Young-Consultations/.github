# Next MVP: approved issue to validated draft pull request

**Status:** Organization-level planning baseline  
**Scope owner:** `Young-Consultations/.github`  
**Normative requirement baseline:** [AI-SDLC control-plane requirements](../requirements/README.md)

## Objective

The next MVP shall demonstrate one human-approved, end-to-end change: an eligible
`portfolio-tasks` issue names exactly one authorized target; a human approves the
current revision; the control plane validates and routes it; the target invokes
Codex, validates the change, and publishes or reuses exactly one draft pull
request; and a canonical result, validation status, and draft-PR link are
correlated to the source issue. Merge, release, deployment, and production
operations remain human-controlled and outside this MVP.

This is a functional interoperability MVP, not a production-readiness claim.

## Compatibility state for this increment

The published immutable compatibility baseline remains `ai-sdlc-v2.3.2` at
commit `5738ace3ee90dde11336f8f8099e64e5645f7139`, using payload
`ai-sdlc-contract/v2` and fixture oracle `TC-MVP-CI-001` version 2.3.0.

Implementation of `TC-MVP-E2E-001-SIM` with the actual result receiver exposed
DEF-0032: the target legitimately returns `draft-pr-created` for the initial
successful delivery and `duplicate-reused` when the same managed draft is found
on redelivery, while the published receiver rejected every non-identical second
result for a delivery as ambiguous. That contradiction prevents truthful REAL
retry acceptance against 2.3.2.

The corrective compatibility candidate is `ai-sdlc-v2.3.3`. It preserves the
v2 payload schemas and narrows receiver retry semantics so
`draft-pr-created -> duplicate-reused` is accepted as an idempotent no-op only
when it represents the same stable managed-draft effect. Every other
non-identical result remains ambiguous and fails closed. The 2.3.2 tag must not
move or be reinterpreted.

`TC-MVP-E2E-001-REAL` is blocked until 2.3.3 is published and the selected
`consulting-playbook` target is bound by reviewed immutable evidence to a target
workflow that consumes the 2.3.3 receiver.

## Business and user value

The demonstration gives task owners a reviewable proposed change rather than an
opaque dispatch, gives maintainers one governed integration contract, and gives
reviewers durable approval, validation, and result evidence. It advances
[BG-01 through BG-07](../requirements/project-requirements.md#goals) while
preserving the vision's human-authority and repository-ownership boundaries.

## Included repositories and responsibilities

| Repository | MVP responsibility | Requirement ownership |
| --- | --- | --- |
| `Young-Consultations/.github` | Own canonical contracts/fixtures, registry, activation, admission, routing, result receiver, compatibility/release policy, and the controlled E2E acceptance harness. | Organization requirements (`GH-*`), ADRs, and shared test identities |
| `Young-Consultations/portfolio-tasks` | Own eligible source issue, revision-bound human approval, exactly-one-target selection, lifecycle projection, and correlated result presentation. | Consumer conformance obligations; repository-specific IDs pending owner confirmation |
| `Young-Consultations/slugger` | Accept only authorized compatible input and perform target execution, validation, idempotent draft publication, and result return when selected. | Consumer conformance obligations; repository-specific IDs pending owner confirmation |
| `Young-Consultations/consulting-playbook` | Perform the same target obligations and serve as the sole initially enabled REAL acceptance target. | Consumer conformance obligations; repository-specific IDs pending owner confirmation |

Repository-specific requirement IDs from sibling repositories require
confirmation by their owners. This repository does not infer sibling behavior
from documentation alone.

## End-to-end acceptance scenario

1. An eligible issue is created in `portfolio-tasks` and identifies exactly one
   registered target and explicit `implement` mode.
2. An authorized human approves the current executable task revision. A
   material edit receives a new `task_id` and requires approval again.
3. The control plane validates the approved task, target, immutable adapter and
   conformance evidence, current activation, contract version, and scope, then
   constructs and routes one canonical execution input using stable task,
   delivery, and correlation identities.
4. Only after successful admission may the source project work as `queued`.
5. The target independently revalidates authorization, contract and local
   policy, invokes Codex for REAL implement mode, validates resulting changes,
   and creates or reuses one managed draft pull request for the delivery.
6. The target returns one canonical `execution-result/v2` through the
   organization result receiver.
7. The receiver validates caller/bindings and durable delivery evidence. An
   identical result replay is a no-op. The only permitted non-identical retry
   transition is `draft-pr-created -> duplicate-reused` for the same stable
   managed-draft effect; it produces no second source projection. Every other
   non-identical result is ambiguous and fails closed.
8. The source issue exposes terminal execution outcome, validation status, and
   draft-PR link correlated to the approved revision. No automation merges,
   releases, deploys, or performs production operations.

## Dual-mode acceptance architecture

Acceptance uses one shared [`TC-MVP-E2E-001`](../acceptance/TC-MVP-E2E-001.md)
architecture with two modes. They are not separate orchestration engines.

### TC-MVP-E2E-001-SIM

SIM is repeatable no-real-effects evidence. It:

- resolves the sole enabled target from current activation;
- resolves the target's exact immutable registered adapter commit;
- executes that target-owned adapter with deterministic fake Codex and
  publication effects;
- sends target-produced canonical results through the actual candidate receiver
  implementation with journal/forwarding effects replaced by in-memory seams;
- proves initial success, managed-draft reuse, equivalent retry no-op behavior,
  exactly one source projection, and conflicting duplicate rejection;
- asserts zero real Codex, branch, commit, push, PR, merge, release, deployment,
  production, or secret-output effects;
- records published baseline 2.3.2, candidate 2.3.3, target adapter identity,
  and `real_acceptance_satisfied: false`.

SIM may run in PR CI and by manual dispatch. Passing SIM is required before REAL
but never satisfies REAL acceptance or MVP completion.

### TC-MVP-E2E-001-REAL

REAL proves the deployed integration that SIM cannot prove: human approval
provenance, GitHub event routing, credentials, real Codex execution, target
validation, draft publication, receiver delivery, source projection, and
redelivery behavior.

REAL is intentionally human-triggered and excluded from normal CI. The control
plane must not synthesize or apply source approval. The existing
`portfolio-tasks` authorized-human `status:approved` event remains the REAL
execution trigger.

Before that human action, REAL preflight must fail closed unless:

- `ai-sdlc-v2.3.3` is published;
- `consulting-playbook` is still the sole enabled target;
- the registry binds the exact immutable consulting adapter and its passing
  conformance report;
- that target workflow consumes the 2.3.3 result receiver;
- fresh SIM evidence passes and explicitly does not claim REAL acceptance;
- required credentials, source revision/approval, harmless scope, and
  draft-only publication policy are confirmed.

REAL may use one harmless documentation-only task, one real Codex execution,
one delivery-owned branch, and exactly one managed draft PR. It must never
merge, release generated work, deploy, change repository/organization settings,
or perform production operations.

## Release and target coordination before REAL

PR #54 prepares the control-plane 2.3.3 candidate with `tag_published: false`.
It is not itself the live acceptance run. After that candidate is reviewed and
merged:

1. update `consulting-playbook` in its own reviewed change so its target workflow
   consumes the corrected receiver from the reviewed 2.3.3 path;
2. run the target's complete no-real-effects conformance harness and publish a
   new immutable adapter tag only after it passes;
3. update the control-plane registry with the exact target tag, commit, and
   report digest;
4. complete the final release review, set `tag_published: true`, pass
   `python scripts/validate_release.py --require-publishable`, merge, and create
   the immutable `ai-sdlc-v2.3.3` tag;
5. rerun REAL preflight;
6. only after preflight passes may an authorized human approve the harmless
   portfolio acceptance issue.

## Continuous interface-validation objective

Normal CI deterministically simulates the approved-issue-to-draft-PR semantics
without paid Codex or real publication. Organization-owned versioned fixtures
are authoritative for valid and invalid task/input/result messages, approval
evidence, registry snapshots, delivery histories, and expected canonical
outcomes.

`TC-MVP-CI-001` covers all registered target profiles and includes valid
request/result, unsupported version, malformed request, unauthorized/stale or
withdrawn approval, unknown/disabled target, duplicate delivery/result,
existing managed draft, target rejection, execution/validation/test/publication
failure, delayed/missing result, ownership conflicts, and no-real-effects
assertions. Consumer evidence remains digest-bound and immutable.

`TC-MVP-E2E-001-SIM` complements that shared matrix by exercising the exact
currently registered target adapter plus the candidate receiver semantics across
the integration seam that DEF-0032 exposed.

## Approval and execution lifecycle

Canonical work states are `proposed`, `approved`, `queued`, `executing`,
`completed`, `failed`, `withdrawn`, `cancelled`, and `superseded`, as defined in
[State Models](../architecture/StateModels.md#work-lifecycle). For v2,
`approved` is the only state admitted at the router boundary. `queued` is a
post-admission source projection and cannot be replayed as authorization.

Retries preserve `delivery_id` and immutable input. Timeout or missing
acknowledgement is uncertain, not success or failure. Reconciliation examines
the authoritative managed-draft/result evidence before retry. Conflicting
ownership or results fail closed for human resolution. A valid terminal source
projection never regresses.

## Contract and interface baseline

The active payload family remains the canonical task, `execution-input/v2`, and
`execution-result/v2` schemas in [`contracts/`](../../contracts/README.md), plus
the four-entry capability registry and repository interfaces RI-01–RI-03 and
RI-MVP-01.

`task_id` identifies an approved source revision; `delivery_id` identifies the
logical at-least-once delivery and remains stable across attempts; attempt
identity is transport evidence, not the idempotency key; `correlation_id` joins
end-to-end evidence.

The result has no separate result ID. Receiver evidence therefore records both
the canonical result digest and a stable visible-effect digest. Identical
results are deduplicated. `draft-pr-created` and `duplicate-reused` may represent
the same managed-draft effect only under the narrow equivalence rule defined in
[`mvp-v2-compatibility.md`](../interfaces/mvp-v2-compatibility.md). All other
non-identical results remain ambiguous.

The organization result receiver owns validation, trusted journal-author policy,
delivery deduplication, forwarding and reconciliation. Targets own result
creation/retry and local draft publication. `portfolio-tasks` owns source issue
presentation. Transport acknowledgement is never execution success.

## CI conformance expectations

The organization fixture release and expected-result manifest are the sole
shared oracle. Each repository maintains only its target/source adapter and
repository-local assertions, pins immutable shared evidence, and commits a
digest-bound report with complete scenario results and zero prohibited effects.
The registry separately binds immutable adapter tag, resolved commit, and report
digest. Disabled, skipped, mutable, incomplete, or locally substituted evidence
is not PASS.

Interface changes cannot be published as an immutable compatibility unit until
producer, router, receiver, source consumer, and affected target profiles have
reviewed passing evidence.

## Success criteria

- `TC-MVP-E2E-001-SIM` passes against the exact immutable adapter of the sole
  enabled target and the candidate receiver with all prohibited real-effect
  counters at zero.
- Published 2.3.2 remains immutable and 2.3.3 is published only after the
  corrected receiver and selected target binding pass release governance.
- REAL preflight fails before paid/mutating effects while 2.3.3 is unpublished
  or the target receiver pin is stale.
- One intentionally approved `TC-MVP-E2E-001-REAL` run ends in one validated
  draft PR and one correlated source projection.
- Redelivery returns/reuses the same managed draft and creates neither a second
  draft PR nor a second source projection.
- REAL is triggered only by the existing authorized-human source approval
  boundary.
- Normal CI invokes no Codex and creates no real implementation branch or PR.
- All automated activity ends at a validated draft proposal plus correlated
  result; merge/release/deploy remain human-controlled.

## Risks and remaining governance dependencies

Remaining work before REAL is implementation/release governance, not an open
architecture decision: target-side receiver repin, new immutable adapter
evidence, registry reconciliation, final 2.3.3 publication, credential review,
and retention/reconciliation settings confirmation.

Risks remain label/provenance drift, incompatible target adapters, ambiguous
delivery acknowledgement, duplicate publication, result loss, excessive
permissions, and simulation/REAL divergence. The dual-mode design reduces the
last risk by using the exact target adapter and actual receiver logic in SIM
while retaining the source-owned human gate and real external effects only in
REAL.

`consulting-playbook` remains the sole enabled target. `.github`,
`portfolio-tasks`, and `slugger` remain disabled pending separate governance
decisions.

## Trace links and requirement allocation

| Layer | Affected baseline |
| --- | --- |
| Vision | [Desired experience and success measures](../VISION.md#desired-end-to-end-experience) |
| Project | [BG-01–BG-07 and MVP success criteria](../requirements/project-requirements.md#success-criteria) |
| Software | [GH-FR-005, GH-FR-008–012, GH-FR-017–018, GH-QR-008](../requirements/software-requirements.md) |
| Interfaces | [Repository interface specification](../requirements/repository-interfaces.md), [MVP v2 compatibility](../interfaces/mvp-v2-compatibility.md) |
| Decisions | [ADR-003, ADR-004, ADR-008–016](../architecture/ADR.md) |
| Architecture/design | [State models](../architecture/StateModels.md), [repository boundaries](../architecture/RepositoryBoundaries.md), [TC-MVP-E2E-001 acceptance design](../acceptance/TC-MVP-E2E-001.md) |
| Traceability | [Requirements RTM](../requirements/requirements-traceability.md), [architecture RTM](../architecture/ArchitectureTraceability.md) |
| Release policy | [Control-plane releases](../releases.md) |
