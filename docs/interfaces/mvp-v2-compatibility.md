# MVP v2 shared-interface and compatibility baseline

**Normative status:** organization-owned baseline for consumer alignment.  
**Payload version:** `ai-sdlc-contract/v2` (v3 is out of scope).  
**Compatibility recovery release:** `2.3.2`, fixture `2.3.0`. It preserves
`ai-sdlc-v2.3.1` and every earlier tag as immutable history. Release 2.3.2
rebinds `portfolio-tasks` and `slugger` to new adapter tags whose conformance
pins include the exact report-producing harness; the unaffected `.github` and
`consulting-playbook` adapters remain on their already verified immutable
2.3.1 tags. The control-plane release never embeds its own future merge SHA,
and mutable `main` is not a compatibility pin.

This document is self-contained so a consumer needs no access to another consumer repository. The four and only four MVP targets are `Young-Consultations/.github`, `Young-Consultations/portfolio-tasks`, `Young-Consultations/slugger`, and `Young-Consultations/consulting-playbook`. The new `.github` entry is disabled-first, and registry enablement remains an explicit reviewed gate; sibling conformance is **pending owner confirmation**.

## Closed canonical payloads

All three schemas use JSON Schema Draft 2020-12, require format checking, and set `additionalProperties: false`. Producers and consumers shall reject missing, extra, malformed, or unsupported-version fields rather than infer or default them.

| Payload | Schema | Required fields | Normative rules |
| --- | --- | --- | --- |
| Canonical task | `contracts/task-contract.schema.json` | `contract_version`, `task_id`, `source_issue`, `status`, `executor`, `project`, `priority`, `task_type`, `target_repository`, `parallel_safe`, `dependencies`, `risk`, `scope`, `instructions`, `created_by` | Router admission requires v2, `status: approved`, `executor: codex`, empty `dependencies`, a matching capability profile, and current control-plane activation. Every material change gets a new `task_id` and new human approval. `queued` is only a post-admission source projection and is rejected as fresh authorization. Approval ID, approver, timestamp, revision digest, and revocation record are deferred to v3 and shall not be added to v2. |
| Execution input | `contracts/execution-input.schema.json` | `contract_version`, `correlation_id`, `delivery_id`, `source_issue`, `target_repository`, `task_type`, `execution_mode`, `project`, `priority`, `executor`, `parallel_safe`, `draft_pr_only`, `instructions`, `requested_branch`, `concurrency_group`, `timeout_minutes` | v2; mode is `verify` or `implement`; executor is `codex`; `draft_pr_only` is true. Verify calls no Codex and creates no branch/PR. Implement may call Codex and create or reuse only one managed open draft PR. |
| Execution result | `contracts/execution-result.schema.json` | `contract_version`, `correlation_id`, `delivery_id`, `execution_status`, `target_repository`, `branch_name`, `pull_request_url`, `workflow_url`, `validation_result`, `test_result`, `failure_category`, `failure_message`, `started_at`, `completed_at` | Status is one of `accepted`, `rejected`, `queued`, `running`, `verified`, `no-changes`, `draft-pr-created`, `blocked`, `failed`, `duplicate-reused`, `ambiguous-rejected`; validation/test are `not-run`, `passed`, or `failed`; failure category is `none`, `contract-validation`, `authorization`, `dependency`, `repository-routing`, `authentication`, `codex-runtime`, `no-changes`, `validation`, `tests`, `publication`, `timeout`, or `unknown`. Verify success is `verified` with null branch/PR. Implementation success is `draft-pr-created` or `duplicate-reused`. Input correlation, delivery, and target identities are copied unchanged. |

`delivery_id` is the stable logical-delivery identity and idempotency key; retries preserve it. `correlation_id` is the end-to-end observability identity. Delivery is at least once, never exactly once. Visible effects are idempotent: at most one managed open draft PR per delivery. The ownership marker is `ai-sdlc-delivery-id`, branch identity derives from `delivery_id`, and targets must preflight, fail closed on uncertain reuse, and requery after create races. Existing managed work returns `duplicate-reused`. A byte-for-byte/canonically identical second result is accepted without another effect; a non-identical result for the delivery is rejected and represented as `ambiguous-rejected`.

## Workflow compatibility matrix

| Interface / owner | Workflow | Required inputs | Required secret | Outputs | Consumer rule |
| --- | --- | --- | --- | --- | --- |
| Router / `.github` control plane | `.github/workflows/codex-router.yml` | Required `task_payload`; optional `execution_mode` (defaults to `implement`) | `CODEX_ROUTER_TOKEN` | `execution_result`, `correlation_id`, `delivery_id`, `failure_category`, `diagnostic_summary`, `concurrency_group` | Admit only the task rules above, an exact capability entry, and current activation. Rejections are represented in `execution_result`; there is no separate `accepted` output. |
| Target adapter / each selected repository | `.github/workflows/codex-execute.yml` in that target, referenced by its registry entry and triggered only by `workflow_dispatch` | Exactly two required strings: `execution_input_json` containing the complete canonical input and `concurrency_group` equal to its canonical value | Target-owned executor credential; exact local name is owned and documented by that target | No reusable-workflow output is returned to the router; the adapter delivers a canonical result to the receiver separately | No `workflow_call`, artifact, run-ID, field-by-field, optional, extra, or fallback interface is active. Must validate again; target credentials cannot route, approve, write another repository, merge, release, or deploy. |
| Result receiver / `.github` control plane | `.github/workflows/codex-result-receiver.yml` | `execution_result` (complete result JSON string), `source_issue` (must equal admitted binding) | Only `CODEX_RESULT_TOKEN`; targets never supply trusted-author policy | String outputs `accepted` (`true`/`false`), `delivery_id`, `correlation_id`, `execution_status`, `failure_category`, `diagnostic_summary` | Behavior and immutable trust ownership are defined below. |

Target-side defense in depth remains mandatory after router activation checks.
Each adapter independently authenticates and authorizes the admitted caller;
validates the exact target, contract version, closed schema and formats,
supported task type and mode, `draft_pr_only: true`, concurrency transport,
delivery identity, idempotency and deterministic ownership; and applies its
local repository security/execution policy. It must not reject solely because
an immutable historical compatibility snapshot happened to record the target
as disabled.

The immutable target-capability registry in `config/codex-repositories.json`
records identity, workflow, version, task-type, draft-only, concurrency,
environment, idempotency policy, and reviewed conformance evidence. Conformance
is `null` while pending and, when present, binds fixture/release identity, exact
adapter tag and commit, report path/digest, PASS status, and sufficiency for
activation. The report identifies a canonical v2 conformance pin containing
exact shared-file and target adapter/harness blob identities. It does not embed
the SHA of its own containing commit; the registry's independently verified
tag-to-commit binding and report digest supply that identity without recursion.
The mutable activation map in `config/codex-activation.json` records
only whether the control plane may currently route to each target. Before
controlled MVP execution, the selected workflow ref must be an owner-reviewed,
non-moving `codex-adapter-vMAJOR.MINOR.PATCH` release tag whose recorded complete
shared-oracle report validates at that ref. The router validates current
activation and evidence before both construction and dispatch. Target adapters
validate the immutable capability and protocol rules but do not consult
activation. Consequently a target may keep one compatibility SHA when activation
later changes.

## Result receiver and source-projection handoff

The reusable receiver is triggered only by `workflow_call`. `execution_result`
and `source_issue` are required strings. `CODEX_RESULT_TOKEN` is the only secret
accepted from a target and is a repository-scoped GitHub App or token identity
authorized only to validate, store, and forward results; it provides no target
code-write, merge, release, or deployment authority. The reusable workflow does
not check out `github.workflow_sha`, because GitHub binds that context to the
caller. It invokes the control-plane-owned `actions/codex-result-receiver`
composite action at the same immutable release commit; the action loads
`config/codex-result-trust.json` from its own downloaded bundle. Live
verification rejects a workflow/action commit mismatch. The target cannot
supply, override, or inherit trusted journal-author identities. An empty or
malformed list denies all results; publication requires reviewed identities for
both admission and result journal roles.

The receiver shall: (1) authenticate the caller; (2) validate the exact v2 result schema with format checking; (3) verify target, delivery, correlation, and source bindings against the admitted delivery record; (4) deduplicate by `delivery_id`; (5) accept identical redelivery without a second visible effect; (6) reject a conflict as ambiguous; (7) preserve durable result evidence; (8) forward exactly one validated projection to the source owner; (9) return sanitized diagnostics only; (10) preserve execution failure rather than reinterpret it as transport success; and (11) never merge, release, deploy, or modify target code.

The forwarded source projection is the validated canonical result plus the separately bound `source_issue`; it contains no receiver-private storage identifiers or credentials. The source owner keys its write by `delivery_id`, verifies `source_issue`, copies `execution_status`, `validation_result`, `test_result`, `pull_request_url`, `failure_category`, and sanitized `failure_message` to its presentation, and stores `correlation_id` and `workflow_url` as trace evidence. Null values remain null. Identical replay returns success without a second issue update. Conflict returns `accepted=false`, `execution_status=ambiguous-rejected`, `failure_category=unknown`, and a sanitized diagnostic; it forwards nothing. Schema/authentication/binding rejection returns `accepted=false`, the safely parsed identities or empty strings, the applicable status/category, and forwards nothing. A validated target `failed` result is successfully received (`accepted=true`) while its `execution_status=failed` remains unchanged; receiver workflow success is not execution success.

Missing results remain pending until the deployment-configured reconciliation deadline, then project `failed`/`timeout`; delayed valid results are accepted only while consistent with the admitted record and stored evidence. Retrying never changes `delivery_id`. Retention duration and timeout values are deployment governance settings, not payload/interface fields.

## Separate `.github` trust boundaries

The `.github` control plane owns contracts, registry, admission, routing, receiver, fixtures, and conformance policy. Its target adapter is a separately authorized target principal used only after the router selects `Young-Consultations/.github`. It may change only this repository, for the registry allowlist (`ci-cd`, `documentation`, `repository-maintenance`, `testing`), and may produce only a validated draft PR and canonical result. It cannot bypass admission, approve its own work, route, alter registry state at runtime, use control-plane credentials, modify another repository, merge, release, deploy, or perform production operations.

## Authoritative no-Codex conformance matrix (`TC-MVP-CI-001`)

The current fixture manifest is the authoritative shared scenario list. The
`.github` adapter's deterministic fake-effects tests supplement that fixture
oracle with target-specific admission, reconciliation, execution, validation,
publication, and no-real-effect coverage. This local evidence does not prove
live cross-repository conformance.

Every row runs for all four target profiles using the released fixtures and fake executor/publication/result adapters. Normal CI has read-only repository permissions and assertions that the Codex-call count, real branch-create count, and real PR-create count are all zero.

| Scenario | Required observation |
| --- | --- |
| Valid verify request | Schema-valid `verified`; null branch/PR; fake executor not invoked. |
| Valid implement request | Fake executor invoked once; simulated `draft-pr-created`; no real branch/PR. |
| Valid result | Receiver accepts once and emits exactly one simulated source projection. |
| Unsupported contract version / malformed payload | Reject `contract-validation`; no dispatch/effect. |
| Non-approved task / queued task at admission | Reject `authorization`; no dispatch/effect. |
| Material change reusing old task ID | Source/router test rejects `authorization`; new ID and approval required. |
| Unknown target / disabled target | Router rejects `repository-routing` before dispatch; target execution is never invoked. A disabled profile remains disabled until evidence and approval. |
| Duplicate delivery | Retry preserves input and ID; no second executor/publication effect. |
| Existing managed draft PR | Verify marker and binding; reuse with `duplicate-reused`; ambiguity fails closed. |
| Identical duplicate result | Accept success; no second evidence projection visible effect. |
| Conflicting duplicate result | Reject as `ambiguous-rejected`; no projection. |
| Target rejection | Preserve `rejected` and category; do not report execution success. |
| Execution failure | `failed` / `codex-runtime`; no PR. |
| Validation failure | `failed` / `validation`; no publish. |
| Test failure | `failed` / `tests`; no publish. |
| Publication failure | `failed` / `publication`; reconcile before retry. |
| Missing result | Pending then deterministic `failed` / `timeout` projection after configured deadline. |
| Delayed result | Accept only if bindings/evidence remain consistent; exactly one projection. |
| Ambiguous result | `ambiguous-rejected`; no new effect; human reconciliation required. |
| No-real-effects proof | Codex, branch, and PR adapter counters are zero and CI token permissions are read-only. |

Consumer evidence records the externally pinned immutable fixture reference,
capability profile, canonical conformance-pin revision, compatibility SHA, every
scenario result, and all no-real-effects counters. The report is committed at
the tagged adapter ref; its SHA-256 digest and the tag's resolved commit are
recorded separately in the registry. The verifier recomputes the pin and every
bound file identity at that ref. A disabled,
skipped, mutable, incomplete, locally substituted, or digest-mismatched adapter
is `not-evaluated` or failed, never organization-wide PASS. Evidence for all four
repositories is currently pending; this recovery candidate does not claim their
conformance.

## Deployment/governance gates (not open interface decisions)

Before a target is enabled, humans must approve its immutable workflow pin,
repository-scoped credentials/environment, evidence retention duration,
reconciliation deadline, control-plane journal-author identities, and
owner-supplied conformance evidence. Before 2.3.2 publication,
`python scripts/validate_release.py --require-publishable` must also pass for
every target and the receiver trust policy. These choices do not change consumer
fields or v2 semantics. Merge, tag/release publication, deployment, and
production operation remain human-controlled; the MVP ends at one validated
draft PR and one correlated canonical result.
