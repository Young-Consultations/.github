# MVP v2 shared-interface and compatibility baseline

**Normative status:** organization-owned baseline for consumer alignment.
**Payload version:** `ai-sdlc-contract/v2` (v3 is out of scope).
**Payload compatibility baseline:** `ai-sdlc-contract/v2`, fixture `2.3.0`.
**Current published control-plane release:** `ai-sdlc-v2.4.5`.

Published `ai-sdlc-v2.3.2` remains immutable historical compatibility evidence
at commit `5738ace3ee90dde11336f8f8099e64e5645f7139`; it is not the current
control-plane release. The backward-compatible receiver retry correction first
published in 2.4.0 remains part of the current 2.4.5 behavior: a target may
return `draft-pr-created` on first successful delivery and `duplicate-reused`
when the same managed draft is found on redelivery, subject to the stable-effect
identity rules below. Later 2.4.x patch releases preserve the closed v2 schemas
while repairing execution/publication boundaries.

The four and only four MVP targets are `Young-Consultations/.github`,
`Young-Consultations/portfolio-tasks`, `Young-Consultations/slugger`, and
`Young-Consultations/consulting-playbook`. All four have registry-bound passing
2.3.2-era compatibility evidence. Mutable activation is separate from immutable
compatibility: `consulting-playbook` is currently the sole enabled target.

## Closed canonical payloads

All three schemas use JSON Schema Draft 2020-12, require format checking, and
set `additionalProperties: false`. Producers and consumers shall reject missing,
extra, malformed, or unsupported-version fields rather than infer or default
them.

| Payload | Schema | Required fields | Normative rules |
| --- | --- | --- | --- |
| Canonical task | `contracts/task-contract.schema.json` | `contract_version`, `task_id`, `source_issue`, `status`, `executor`, `project`, `priority`, `task_type`, `target_repository`, `parallel_safe`, `dependencies`, `risk`, `scope`, `instructions`, `created_by` | Router admission requires v2, `status: approved`, `executor: codex`, empty `dependencies`, a matching capability profile, and current control-plane activation. Every material change gets a new `task_id` and new human approval. `queued` is only a post-admission source projection and is rejected as fresh authorization. Approval ID, approver, timestamp, revision digest, and revocation record are deferred to v3 and shall not be added to v2. |
| Execution input | `contracts/execution-input.schema.json` | `contract_version`, `correlation_id`, `delivery_id`, `source_issue`, `target_repository`, `task_type`, `execution_mode`, `project`, `priority`, `executor`, `parallel_safe`, `draft_pr_only`, `instructions`, `requested_branch`, `concurrency_group`, `timeout_minutes` | v2; mode is `verify` or `implement`; executor is `codex`; `draft_pr_only` is true. Verify calls no Codex and creates no branch/PR. Implement may call Codex and create or reuse only one managed open draft PR. |
| Execution result | `contracts/execution-result.schema.json` | `contract_version`, `correlation_id`, `delivery_id`, `execution_status`, `target_repository`, `branch_name`, `pull_request_url`, `workflow_url`, `validation_result`, `test_result`, `failure_category`, `failure_message`, `started_at`, `completed_at` | Status is one of `accepted`, `rejected`, `queued`, `running`, `verified`, `no-changes`, `draft-pr-created`, `blocked`, `failed`, `duplicate-reused`, `ambiguous-rejected`; validation/test are `not-run`, `passed`, or `failed`; failure category is `none`, `contract-validation`, `authorization`, `dependency`, `repository-routing`, `authentication`, `codex-runtime`, `no-changes`, `validation`, `tests`, `publication`, `timeout`, or `unknown`. Verify success is `verified` with null branch/PR. Implementation success is `draft-pr-created` or `duplicate-reused`. Input correlation, delivery, and target identities are copied unchanged. |

`delivery_id` is the stable logical-delivery identity and idempotency key;
retries preserve it. `correlation_id` is the end-to-end observability identity.
Delivery is at least once, never exactly once. Visible effects are idempotent:
at most one managed open draft PR per delivery. The ownership marker is
`ai-sdlc-delivery-id`, branch identity derives from `delivery_id`, and targets
must preflight, fail closed on uncertain reuse, and requery after create races.
Existing managed work returns `duplicate-reused`.

Receiver deduplication distinguishes canonical-result identity from stable
visible-effect identity. A canonically identical second result is accepted
without another visible effect. The one permitted non-identical retry transition
is `draft-pr-created` to `duplicate-reused` for the same delivery when contract,
target, correlation, branch, pull-request URL, validation result, test result,
and failure category describe the same managed-draft effect. Attempt metadata
such as timestamps and workflow URL does not change that stable effect. The
equivalent redelivery is accepted as an idempotent no-op and is not projected a
second time. Any other non-identical result for the delivery, including a
different managed branch/PR or an unapproved status transition, is rejected and
represented as `ambiguous-rejected`.

## Workflow compatibility matrix

| Interface / owner | Workflow | Required inputs | Required secret | Outputs | Consumer rule |
| --- | --- | --- | --- | --- | --- |
| Router / `.github` control plane | `.github/workflows/codex-router.yml` | Required `task_payload`; optional `execution_mode` (defaults to `implement`) | `CODEX_ROUTER_TOKEN` | `execution_result`, `correlation_id`, `delivery_id`, `failure_category`, `diagnostic_summary`, `concurrency_group` | Admit only the task rules above, an exact capability entry, and current activation. Rejections are represented in `execution_result`; there is no separate `accepted` output. |
| Target adapter / selected repository | `.github/workflows/codex-execute.yml` at its registry-bound immutable adapter ref, triggered only by `workflow_dispatch` | Exactly two required strings: `execution_input_json` and matching `concurrency_group` | Target-owned executor/publication credentials | No reusable-workflow output is returned to the router; target delivers a canonical result to the receiver separately | No fallback interface is active. Target revalidates identity/contract/policy and can publish only a managed draft. |
| Result receiver / `.github` control plane | `.github/workflows/codex-result-receiver.yml` | `execution_result`, `source_issue` | Only `CODEX_RESULT_TOKEN`; targets never supply trusted-author policy | `accepted`, `delivery_id`, `correlation_id`, `execution_status`, `failure_category`, `diagnostic_summary` | Authenticate, bind, deduplicate/reconcile, durably record, and forward at most one source projection. |

Target-side defense in depth remains mandatory after router activation checks.
Each adapter independently authenticates and authorizes the admitted caller;
validates the exact target, contract version, closed schema and formats,
supported task type and mode, `draft_pr_only: true`, concurrency transport,
delivery identity, idempotency and deterministic ownership; and applies its
local repository security/execution policy. A target must not reject solely
because an immutable historical compatibility snapshot recorded a different
activation state.

The immutable target-capability registry in `config/codex-repositories.json`
records identity, workflow, contract, task types, draft-only policy, concurrency,
environment, idempotency policy, and reviewed conformance evidence. Conformance
binds fixture/release identity, exact adapter tag and resolved commit, report
path/digest, PASS status, and activation-evidence sufficiency. The report uses a
non-recursive conformance pin for shared and target file identities; the
registry separately binds the adapter tag to its commit and report digest.

The mutable activation map in `config/codex-activation.json` records only
whether the control plane may currently route to each target. Before controlled
MVP execution, the selected workflow ref must be an owner-reviewed non-moving
`codex-adapter-vMAJOR.MINOR.PATCH` tag whose recorded complete shared-oracle
report validates at that ref. The router validates current activation and
evidence before construction/dispatch. Target adapters validate immutable
capability/protocol rules but do not consult activation.

## Result receiver and source-projection handoff

The reusable receiver is triggered only by `workflow_call`. `execution_result`
and `source_issue` are required strings. `CODEX_RESULT_TOKEN` is the only secret
accepted from a target and is authorized only to validate, store, and forward
results; it provides no target code-write, merge, release, or deployment
authority.

The receiver invokes the control-plane-owned
`actions/codex-result-receiver` composite action from its own immutable release
bundle. The action loads `config/codex-result-trust.json` from that same bundle.
The target cannot supply, override, or inherit trusted journal-author identities.
An empty or malformed role allowlist denies all results.

The principal resolved from `CODEX_RESULT_TOKEN` must be one of the immutable
`trusted_result_authors` and must not also be an admission author. The same
release bundle exposes `actions/codex-result-credential-preflight` so an
implementation target can verify the result-writer principal and source
repository access before invoking a cost-bearing execution provider. The
receiver repeats that authentication before it writes receipt or forwarding
journal state.

The receiver shall:

1. authenticate the caller;
2. validate exact `execution-result/v2` schema and formats;
3. verify target, delivery, correlation, and source binding against the admitted delivery record;
4. deduplicate by `delivery_id`;
5. accept identical redelivery without another visible effect;
6. accept `duplicate-reused` as an equivalent no-op only when the stable managed-draft effect matches the previously received successful managed-draft effect;
7. reject every other non-identical conflict as ambiguous;
8. preserve durable evidence containing canonical-result and stable-effect digests without storing the full payload;
9. forward exactly one validated source projection;
10. return sanitized diagnostics only;
11. preserve target execution failure rather than reinterpret it as receiver success;
12. never merge, release, deploy, or modify target code.

The forwarded projection is the validated canonical result plus the separately
bound `source_issue`; it contains no receiver-private credential or storage
identifier. The source owner keys its visible update by `delivery_id`, verifies
`source_issue`, and presents the execution/validation/test/PR/failure evidence.
An identical replay or equivalent managed-draft `duplicate-reused` redelivery
returns success without a second issue update. Any other conflict returns
`accepted=false`, `execution_status=ambiguous-rejected`, and forwards nothing.
A validated target `failed` result is successfully received while its
`execution_status=failed` remains unchanged; receiver success is not execution
success.

Missing results remain pending until the deployment-configured reconciliation
deadline, then project the approved timeout failure. Retrying never changes
`delivery_id`. Retention duration and timeout values are deployment governance
settings, not payload/interface fields.

## Separate `.github` trust boundaries

The `.github` control plane owns contracts, registry, activation, admission,
routing, receiver, fixtures, and conformance/release policy. Its own target
adapter is a separately authorized target principal used only after the router
selects `Young-Consultations/.github`. It may change only that repository within
its target allowlist and may produce only a validated draft PR plus canonical
result. It cannot bypass admission, approve its own work, route, alter registry
state at runtime, use control-plane credentials, modify another repository,
merge, release, deploy, or perform production operations.

## Authoritative no-Codex conformance matrix (`TC-MVP-CI-001`)

The current fixture manifest is the authoritative shared scenario list. Every
registered target maintains repository-owned adapter/harness evidence against
that oracle. Normal CI is read-only and uses deterministic fake external-effect
adapters.

| Scenario | Required observation |
| --- | --- |
| Valid verify request | Schema-valid `verified`; null branch/PR; fake executor not invoked. |
| Valid implement request | Fake executor invoked once; simulated `draft-pr-created`; no real branch/PR. |
| Valid result | Receiver accepts once and emits exactly one simulated source projection. |
| Unsupported contract version / malformed payload | Reject `contract-validation`; no dispatch/effect. |
| Non-approved / stale / withdrawn / queued task at admission | Reject before dispatch/effect. |
| Material change reusing old task ID | Reject; new task ID and fresh approval required. |
| Unknown / disabled target | Router rejects before dispatch; disabled is never PASS-by-skip. |
| Duplicate delivery | Retry preserves input/ID and creates no second executor/publication effect. |
| Existing managed draft | Verify marker/binding and return `duplicate-reused`; ambiguity fails closed. |
| Identical duplicate result | Accept no-op; no second source projection. |
| Equivalent managed-draft duplicate result | `draft-pr-created` followed by `duplicate-reused` for the same stable managed-draft effect is a no-op; no second projection. |
| Conflicting duplicate result | Any other non-identical result is `ambiguous-rejected`; no projection. |
| Target / execution / validation / test / publication failure | Preserve canonical failure category; no unauthorized publication. |
| Missing / delayed / ambiguous result | Reconcile using durable binding/evidence and fail closed on conflict. |
| No-real-effects proof | Codex, branch, commit, push, PR, merge, release, deployment, production and secret-output counters remain zero. |

Consumer evidence records the pinned fixture identity, capability profile,
canonical conformance-pin revision, compatibility SHA, complete scenario
results, and all prohibited-effect counters. The report is committed at the
immutable adapter ref; its SHA-256 digest and the tag's resolved commit are
recorded separately in the registry.

The published 2.3.2 registry contains passing evidence for all four current
adapter profiles. For 2.4.0 publication, the receiver correction requires fresh
review of the affected consumer path. In particular, `consulting-playbook` must
publish new immutable adapter evidence after its target workflow consumes the
2.4.0 receiver. Existing 2.3.2-era evidence is history and cannot prove the new
receiver binding.

## Deployment/governance gates

### Current 2.4.5 state

The current published control-plane release is `ai-sdlc-v2.4.5`. Publication
attestation, deployed Runtime Preflight, immutable REAL preflight, and the source
consumer repin are complete. Fresh issue #154 verified the initial live route
through human approval, routing, target execution, validation/tests, managed
draft publication, receiver delivery, and source projection.

The full REAL acceptance decision is **not yet complete** because the required
equivalent redelivery/idempotency exercise remains outstanding under
portfolio-tasks #121. A published release and successful initial live path do not
substitute for that separate acceptance evidence.

Published 2.4.4 is immutable historical evidence but is not an execution-safe
rollback for cost-bearing implementation after REAL issue #151. Rollback
handling must follow `docs/releases.md` and keep implementation dispatch
disabled when no separately reviewed safe rollback is available.

### Historical 2.4.0 publication gates

The former 2.4.0 candidate sequence required structural validation, target
conformance, registry binding, credentials/settings review, publishability, and
creation of an immutable 2.4.0 tag. Those gates are retained as historical
evidence of the compatibility correction that introduced the receiver's
equivalent managed-draft retry semantics. They are not current publication
instructions and `tag_published: false` does not describe the current 2.4.5
release state.

Merge, release publication, deployment, and production operation remain
human-controlled; this MVP's automated publication boundary remains one managed
draft PR and one correlated source projection.
