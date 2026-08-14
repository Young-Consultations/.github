# Next MVP: approved issue to validated draft pull request

**Status:** Organization-level planning baseline<br>
**Scope owner:** `Young-Consultations/.github`<br>
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

## Business and user value

The demonstration gives task owners a reviewable proposed change rather than an
opaque dispatch, gives maintainers one governed integration contract, and gives
reviewers durable approval, validation, and result evidence. It advances
[BG-01 through BG-07](../requirements/project-requirements.md#goals) while
preserving the vision's human-authority and repository-ownership boundaries.

## Included repositories and responsibilities

| Repository | MVP responsibility | Requirement ownership |
| --- | --- | --- |
| `Young-Consultations/.github` | Own canonical contracts/fixtures, registry, admission, routing, result-consumption and journal-author trust rules, conformance suite, and this baseline. It is both the control plane and, behind a separate trust boundary and target-only credentials, a bounded execution target for explicitly selected organization documentation, CI, repository-maintenance, and testing work. | Organization requirements (`GH-*`), ADRs, and shared test identities |
| `Young-Consultations/portfolio-tasks` | Own eligible source issue, revision-bound human approval, exactly-one-target selection, lifecycle projection, and consumption/presentation of the correlated result; implement target duties when selected. | Consumer conformance obligations; repository-specific IDs pending owner confirmation |
| `Young-Consultations/slugger` | Accept only authorized compatible input and perform target execution, validation, idempotent draft publication, and result return when selected. | Consumer conformance obligations; repository-specific IDs pending owner confirmation |
| `Young-Consultations/consulting-playbook` | Perform the same target obligations without assuming undocumented package paths or APIs. | Consumer conformance obligations; repository-specific IDs pending owner confirmation |

Repository-specific requirement IDs from sibling repositories **require
confirmation by their owners**. This repository cannot verify their current
implementation or documentation.

## End-to-end acceptance scenario

1. An eligible issue is created in `portfolio-tasks` and identifies exactly one
   of the four registered targets and an explicit `implement` mode.
2. An authorized human approves the current executable task. The producer emits
   a canonical v2 task with `status: approved`; a material edit is represented
   by a new `task_id` and requires approval again.
3. The control plane validates the approved task, target, immutable adapter and
   conformance evidence, registry enablement, contract version, and scope, then
   constructs and routes one canonical execution input using stable task,
   delivery, and correlation IDs. Dynamic invocation uses only
   `workflow_dispatch` with required `execution_input_json` and
   `concurrency_group` strings.
4. Only after successful admission may the source project the work as `queued`.
   A queued v2 task is not accepted as fresh router input because v2 carries no
   separate approval record with which to re-establish authorization.
5. The target independently validates compatibility, invokes
   Codex, validates resulting changes, and creates or reuses one managed draft
   pull request for the delivery ID.
6. The target returns one canonical `execution-result/v2` through the result
   receiver described below. The control plane validates and idempotently
   forwards it to the source issue owner.
7. The source issue exposes terminal execution outcome, validation status, and
   draft-PR link correlated to the approved revision. No automation merges,
   releases, deploys, or performs production operations.

Acceptance requires the planned `TC-MVP-E2E-001` controlled integration test
and all simulated cases in `TC-MVP-CI-001`; a dispatch acknowledgement alone is
not success.

## Continuous interface-validation objective

Normal CI shall deterministically simulate the entire approved-issue-to-draft-PR
process for all four registered targets without Codex, a real implementation
branch, or a real pull request. Organization-owned versioned fixtures are authoritative for
valid and invalid task/input/result messages, approval evidence, registry
snapshots, delivery histories, and expected canonical outcomes. Mocks, stubs,
or test adapters shall exercise approval, construction, selection, target
acceptance, simulated execution/validation/publication, result generation,
return and consumption, redelivery, and reconciliation.

`TC-MVP-CI-001` shall cover each supported target and: valid request/result;
unsupported version; malformed request; unauthorized, stale, or withdrawn
approval; unknown or disabled target; duplicate delivery/result; existing
managed draft PR; target rejection; execution or validation failure; and
delayed, missing, or ambiguous result. CI shall fail when a consumer's pinned
contract or declared adapter is incompatible. A consumer demonstrates
conformance by running the shared fixture suite against its own adapter and
publishing the versioned report; it need not access sibling repositories.

At least one separately controlled, intentionally initiated
`TC-MVP-E2E-001` test may use a real approved issue, Codex, target branch, and
draft PR. It is excluded from normal CI, uses scoped credentials and an
explicit human gate, never merges, and cleans up only under human control.

## Included capabilities and exclusions

Included: approved v2 task admission; canonical construction; four-target
registration and gated enablement; deterministic routing; `verify` and
`implement` modes; target execution and validation; at-least-once-safe result
return; draft-PR discovery/reuse; source correlation; deterministic conformance
simulation; and controlled real-path evidence.

The shared fixture set currently provides the authoritative scenario catalog
and canonical examples, but not executable inputs and expected outputs for
every scenario. Completing those repository-owned fixture artifacts and the
no-real-effects harness is planned implementation work under `GH-QR-008`; their
absence is not evidence of shared executable or live cross-repository
conformance.

Excluded: exactly-once transport; autonomous approval; automatic merge;
release, deployment, production operation, or production-scale SLOs; unrelated
features; and claims of production readiness. `verify` is read-only and returns
verification evidence without Codex, branch, or PR. `implement` permits Codex
and draft-only publication after approval.

## Approval and execution lifecycle

Canonical work states are `proposed`, `approved`, `queued`, `executing`,
`completed`, `failed`, `withdrawn`, `cancelled`, and `superseded`, as defined in
[State Models](../architecture/StateModels.md#work-lifecycle). For this v2 MVP, `approved` is the only state admitted at the router
boundary. `queued` is a post-admission source projection and cannot be replayed as
authorization. A material edit receives a new task ID and fresh approval. Revocation before execution produces `withdrawn`; cancellation
during execution requests best-effort stop and forbids new side effects, but
does not erase evidence or guarantee interruption of an already-running actor.

Retries and replays preserve delivery ID and immutable payload. Timeout or
missing acknowledgement is uncertain, not failure or success. Reconciliation
queries the authoritative result and managed draft-PR marker before retry.
Conflicting results or ownership are `ambiguous` and fail closed for human
resolution. A valid terminal state never regresses.

## Contract and interface baseline

The baseline is the canonical task, `execution-input/v2`, and
`execution-result/v2` contract family in [`contracts/`](../../contracts/README.md),
the four-entry registry policy, and repository interfaces
[RI-01–RI-03 and RI-MVP-01](../requirements/repository-interfaces.md). Task
ID identifies the approved source-work revision; delivery ID identifies the
logical at-least-once delivery and remains
stable across attempts; attempt ID (transport metadata, not the idempotency key)
identifies an invocation; correlation ID joins evidence across the flow. The v2
result has no
separate result ID, so receivers deduplicate by delivery ID and reject a second
non-identical result for that delivery as ambiguous.

The MVP result transport is an organization-owned, reusable result-receiver
workflow invoked by targets with a canonical result, authenticated caller
identity, and only a narrowly scoped result-delivery credential. The receiver
invokes a self-pinned control-plane action that loads trusted journal-author
identities from the same immutable release commit; the target cannot supply or
inherit that policy. It
validates schema, target identity, delivery/correlation binding, and
delivery-ID uniqueness, stores durable evidence, and idempotently dispatches the
validated result to the source owner for issue projection. Targets own result
creation and retry; `.github` owns receiver validation/forwarding and
reconciliation; `portfolio-tasks` owns issue presentation. Transport
acknowledgement is not execution success.

## CI conformance expectations

The organization fixture release and expected-result manifest are the sole
shared oracle. Each repository maintains only its adapter and repository-local
assertions, pins an immutable fixture release, tests both modes and every shared
case applicable to its role, and commits a digest-bound report recording the
exact adapter tag/commit, compatibility SHA, complete scenario results, and zero
Codex/publication/merge/release/deployment/secret-output effects. Normal CI uses
fake Codex and publication adapters and is denied write permissions. Disabled,
skipped, mutable, or locally substituted evidence is not PASS. Interface changes
cannot merge until producer, router, receiver, source consumer, and all four
target profiles pass.

## Success criteria

- One intentionally approved real-path run ends in one validated draft PR and
  a schema-valid result visibly correlated to the source issue.
- All four registered targets pass the shared simulated matrix before enablement; a target
  that has not passed remains disabled.
- Every material revision has a distinct task ID and fresh `approved` state; stale, withdrawn,
  unknown, incompatible, or ambiguous work creates no new implementation side
  effect.
- Redelivery and duplicate results cause idempotent visible effects: at most one
  managed open draft PR and one source-issue projection per delivery.
- Normal CI invokes no Codex and creates no real branch or PR, and a deliberately
  incompatible consumer fixture causes CI failure.
- All automated activity ends at a validated draft PR plus correlated result.

## Assumptions, constraints, risks, and unresolved decisions

Assumptions requiring consumer confirmation: `portfolio-tasks` can emit the
approved v2 task before projecting `queued`; every target can validate and emit
`execution-result/v2`; all targets can discover a managed draft by delivery
marker; and consumers can call the reusable result receiver without supplying
its trust policy. External
observations report that `portfolio-tasks` may replace `status:approved` with
`status:queued`, Slugger may require `ai-sdlc-approved`, Consulting Playbook may
recheck `status:approved`, registered targets may be disabled, and Consulting
Playbook may assume unexposed package paths/APIs. These are **not verified here**
and require owner confirmation and conformance evidence.

Risks are label/provenance drift, incompatible target adapters, ambiguous
delivery acknowledgement, duplicate publication, result loss, permissions
that exceed the MVP boundary, and a simulation that diverges from the real
path. The ADRs below resolve approval and result transport for the MVP; no
organization-level implementation-blocking decision remains open. Owners must
still approve the result journal-author identities, credentials, retention
duration, and each target's enablement as deployment/governance decisions before
the controlled real test. Until then the receiver author allowlist is
empty/deny-all and every target remains disabled.

## Trace links and requirement allocation

| Layer | Affected baseline |
| --- | --- |
| Vision | [Desired experience and success measures](../VISION.md#desired-end-to-end-experience) |
| Project | [BG-01–BG-07 and MVP success criteria](../requirements/project-requirements.md#success-criteria) |
| Software | [GH-FR-005, GH-FR-008–012, GH-FR-017–018, GH-QR-008](../requirements/software-requirements.md) |
| Interfaces | [Repository interface specification](../requirements/repository-interfaces.md), [external interfaces](../requirements/external-interfaces.md) |
| Decisions | [ADR-003, ADR-004, ADR-008–014](../architecture/ADR.md) |
| Architecture/design | [State models](../architecture/StateModels.md), [sequence diagrams](../architecture/SequenceDiagrams.md), [data flow](../architecture/DataFlow.md), [repository boundaries](../architecture/RepositoryBoundaries.md) |
| Traceability | [Requirements RTM](../requirements/requirements-traceability.md), [architecture RTM](../architecture/ArchitectureTraceability.md) |
| Release policy | [Control-plane releases](../releases.md) |

| Repository | Included organization IDs | Repository-specific included IDs | Deferred IDs |
| --- | --- | --- | --- |
| `.github` | GH-FR-001–015, GH-FR-017–018, GH-QR-001–008 | N/A (organization owner) | GH-FR-016 and other production-maturity work not needed for MVP |
| `portfolio-tasks` | GH-FR-005/008/010/017/018, GH-QR-008; CC-MVP-SOURCE/CC-MVP-TARGET | **Owner to confirm** | **Owner to record** |
| `slugger` | GH-FR-002/008–012/017/018, GH-QR-008; CC-MVP-TARGET | **Owner to confirm** | **Owner to record** |
| `consulting-playbook` | GH-FR-002/008–012/017/018, GH-QR-008; CC-MVP-TARGET | **Owner to confirm** | **Owner to record** |
