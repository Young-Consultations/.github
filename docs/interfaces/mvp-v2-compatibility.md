# MVP v2 shared-interface and compatibility baseline

**Normative status:** organization-owned baseline for consumer alignment.  
**Payload version:** `ai-sdlc-contract/v2` (v3 is out of scope).  
**Immutable organization reference:** `f2491872976a4dcc1633997954c03c07cbc4fced`.
**Fixture identity:** `tests/fixtures/mvp-v2/manifest.json` at that complete SHA. The declared `ai-sdlc-v2.2.0` tag does not exist, and mutable `main` is not a compatibility pin.

This document is self-contained so a consumer needs no access to another consumer repository. The four and only four MVP targets are `Young-Consultations/.github`, `Young-Consultations/portfolio-tasks`, `Young-Consultations/slugger`, and `Young-Consultations/consulting-playbook`. The new `.github` entry is disabled-first, and registry enablement remains an explicit reviewed gate; sibling conformance is **pending owner confirmation**.

## Closed canonical payloads

All three schemas use JSON Schema Draft 2020-12, require format checking, and set `additionalProperties: false`. Producers and consumers shall reject missing, extra, malformed, or unsupported-version fields rather than infer or default them.

| Payload | Schema | Required fields | Normative rules |
| --- | --- | --- | --- |
| Canonical task | `contracts/task-contract.schema.json` | `contract_version`, `task_id`, `source_issue`, `status`, `executor`, `project`, `priority`, `task_type`, `target_repository`, `parallel_safe`, `dependencies`, `risk`, `scope`, `instructions`, `created_by` | Router admission requires v2, `status: approved`, `executor: codex`, empty `dependencies`, and an enabled registry target/type. Every material change gets a new `task_id` and new human approval. `queued` is only a post-admission source projection and is rejected as fresh authorization. Approval ID, approver, timestamp, revision digest, and revocation record are deferred to v3 and shall not be added to v2. |
| Execution input | `contracts/execution-input.schema.json` | `contract_version`, `correlation_id`, `delivery_id`, `source_issue`, `target_repository`, `task_type`, `execution_mode`, `project`, `priority`, `executor`, `parallel_safe`, `draft_pr_only`, `instructions`, `requested_branch`, `concurrency_group`, `timeout_minutes` | v2; mode is `verify` or `implement`; executor is `codex`; `draft_pr_only` is true. Verify calls no Codex and creates no branch/PR. Implement may call Codex and create or reuse only one managed open draft PR. |
| Execution result | `contracts/execution-result.schema.json` | `contract_version`, `correlation_id`, `delivery_id`, `execution_status`, `target_repository`, `branch_name`, `pull_request_url`, `workflow_url`, `validation_result`, `test_result`, `failure_category`, `failure_message`, `started_at`, `completed_at` | Status is one of `accepted`, `rejected`, `queued`, `running`, `verified`, `no-changes`, `draft-pr-created`, `blocked`, `failed`, `duplicate-reused`, `ambiguous-rejected`; validation/test are `not-run`, `passed`, or `failed`; failure category is `none`, `contract-validation`, `authorization`, `dependency`, `repository-routing`, `authentication`, `codex-runtime`, `no-changes`, `validation`, `tests`, `publication`, `timeout`, or `unknown`. Verify success is `verified` with null branch/PR. Implementation success is `draft-pr-created` or `duplicate-reused`. Input correlation, delivery, and target identities are copied unchanged. |

`delivery_id` is the stable logical-delivery identity and idempotency key; retries preserve it. `correlation_id` is the end-to-end observability identity. Delivery is at least once, never exactly once. Visible effects are idempotent: at most one managed open draft PR per delivery. The ownership marker is `ai-sdlc-delivery-id`, branch identity derives from `delivery_id`, and targets must preflight, fail closed on uncertain reuse, and requery after create races. Existing managed work returns `duplicate-reused`. A byte-for-byte/canonically identical second result is accepted without another effect; a non-identical result for the delivery is rejected and represented as `ambiguous-rejected`.

## Workflow compatibility matrix

| Interface / owner | Workflow | Required inputs | Required secret | Outputs | Consumer rule |
| --- | --- | --- | --- | --- | --- |
| Router / `.github` control plane | `.github/workflows/codex-router.yml` | Required `task_payload`; optional `execution_mode` (defaults to `implement`) | `CODEX_ROUTER_TOKEN` | `execution_result`, `correlation_id`, `delivery_id`, `failure_category`, `diagnostic_summary`, `concurrency_group` | Admit only the task rules above and an enabled exact registry entry. Rejections are represented in `execution_result`; there is no separate `accepted` output. |
| Target adapter / each selected repository | `.github/workflows/codex-execute.yml` in that target, referenced by its registry entry | `execution_input_json` containing the complete canonical input; required `concurrency_group` transport input | Target-owned executor credential; exact local name is owned and documented by that target | No reusable-workflow output is returned to the router; the adapter delivers a canonical result to the receiver separately | Must validate again; target credentials cannot route, approve, write another repository, merge, release, or deploy. |
| Result receiver / `.github` control plane | `.github/workflows/codex-result-receiver.yml` | `execution_result` (complete result JSON string), `source_issue` (must equal admitted binding) | `CODEX_RESULT_TOKEN` | String outputs `accepted` (`true`/`false`), `delivery_id`, `correlation_id`, `execution_status`, `failure_category`, `diagnostic_summary` | Behavior is defined below. |

The registry snapshot currently records `Young-Consultations/<repo>/.github/workflows/codex-execute.yml@main`, including the `.github` target. Those values are routing configuration, not normative compatibility pins. Before controlled MVP execution, the deployment gate must record the owner-reviewed immutable revision resolved from each selected adapter ref. Registry enabled/disabled state, routing rules, and task-type allowlists remain canonical in `config/codex-repositories.json`.

## Result receiver and source-projection handoff

The reusable receiver is triggered only by `workflow_call`. `execution_result` and `source_issue` are required strings. `CODEX_RESULT_TOKEN` is a required repository-scoped GitHub App or token identity authorized only to validate, store, and forward results; it provides no target code-write, merge, release, or deployment authority.

The receiver shall: (1) authenticate the caller; (2) validate the exact v2 result schema with format checking; (3) verify target, delivery, correlation, and source bindings against the admitted delivery record; (4) deduplicate by `delivery_id`; (5) accept identical redelivery without a second visible effect; (6) reject a conflict as ambiguous; (7) preserve durable result evidence; (8) forward exactly one validated projection to the source owner; (9) return sanitized diagnostics only; (10) preserve execution failure rather than reinterpret it as transport success; and (11) never merge, release, deploy, or modify target code.

The forwarded source projection is the validated canonical result plus the separately bound `source_issue`; it contains no receiver-private storage identifiers or credentials. The source owner keys its write by `delivery_id`, verifies `source_issue`, copies `execution_status`, `validation_result`, `test_result`, `pull_request_url`, `failure_category`, and sanitized `failure_message` to its presentation, and stores `correlation_id` and `workflow_url` as trace evidence. Null values remain null. Identical replay returns success without a second issue update. Conflict returns `accepted=false`, `execution_status=ambiguous-rejected`, `failure_category=unknown`, and a sanitized diagnostic; it forwards nothing. Schema/authentication/binding rejection returns `accepted=false`, the safely parsed identities or empty strings, the applicable status/category, and forwards nothing. A validated target `failed` result is successfully received (`accepted=true`) while its `execution_status=failed` remains unchanged; receiver workflow success is not execution success.

Missing results remain pending until the deployment-configured reconciliation deadline, then project `failed`/`timeout`; delayed valid results are accepted only while consistent with the admitted record and stored evidence. Retrying never changes `delivery_id`. Retention duration and timeout values are deployment governance settings, not payload/interface fields.

## Separate `.github` trust boundaries

The `.github` control plane owns contracts, registry, admission, routing, receiver, fixtures, and conformance policy. Its target adapter is a separately authorized target principal used only after the router selects `Young-Consultations/.github`. It may change only this repository, for the registry allowlist (`ci-cd`, `documentation`, `repository-maintenance`, `testing`), and may produce only a validated draft PR and canonical result. It cannot bypass admission, approve its own work, route, alter registry state at runtime, use control-plane credentials, modify another repository, merge, release, deploy, or perform production operations.

## Authoritative no-Codex conformance matrix (`TC-MVP-CI-001`)

The current fixture manifest is the authoritative scenario list. Executable
inputs and expected outputs do not yet exist for every row; completing them and
the deterministic fake adapters is explicitly planned `.github`
implementation work under `GH-QR-008`. Until that work is complete, this matrix
defines required coverage but does not prove shared executable fixture or live
cross-repository conformance.

Every row runs for all four target profiles using the released fixtures and fake executor/publication/result adapters. Normal CI has read-only repository permissions and assertions that the Codex-call count, real branch-create count, and real PR-create count are all zero.

| Scenario | Required observation |
| --- | --- |
| Valid verify request | Schema-valid `verified`; null branch/PR; fake executor not invoked. |
| Valid implement request | Fake executor invoked once; simulated `draft-pr-created`; no real branch/PR. |
| Valid result | Receiver accepts once and emits exactly one simulated source projection. |
| Unsupported contract version / malformed payload | Reject `contract-validation`; no dispatch/effect. |
| Non-approved task / queued task at admission | Reject `authorization`; no dispatch/effect. |
| Material change reusing old task ID | Source/router test rejects `authorization`; new ID and approval required. |
| Unknown target / disabled target | Reject `repository-routing`; a disabled profile remains disabled until evidence and approval. |
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

Consumer evidence records the immutable fixture reference, registry profile, adapter revision, scenario results, and no-real-effects counters. `.github` evidence is locally verifiable; evidence for the three sibling repositories remains **pending owner confirmation** and this baseline does not claim their conformance.

## Deployment/governance gates (not open interface decisions)

Before a target is enabled, humans must approve its immutable workflow pin, repository-scoped credentials/environment, evidence retention duration, reconciliation deadline, and owner-supplied conformance evidence. These choices do not change consumer fields or v2 semantics. Merge, release, deployment, and production operation remain human-controlled; the MVP ends at one validated draft PR and one correlated canonical result.
