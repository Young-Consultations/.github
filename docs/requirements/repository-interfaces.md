# Repository Interface Specification

## Contract rules

All production interfaces shall use immutable version references, canonical payload versions, explicit authorization, stable identity, sanitized failures, and owner-approved change control. Direction is relative to `.github`. Other repository behavior is inferred and must be confirmed during interface review.

## Interface inventory

| ID / repository | Purpose and direction | Inputs to `.github` | Outputs from `.github` | Trigger / contract | Ownership and versioning |
| --- | --- | --- | --- | --- | --- |
| RI-01 `portfolio-tasks` | Primary producer; also registered target. Bidirectional. | Closed-v2 approved task and issue identity; execution result/compatibility evidence when targeted. Rich approval provenance stays source-local. | Validation/routing result; canonical execution input; contract and adoption guidance | Explicit approved-task event invokes router; task, input, result schemas | Portfolio owner owns intent/approval and local execution; control plane owns interchange. Immutable release/payload pin. |
| RI-02 `slugger` | Software-factory execution target. Outbound dispatch; inbound evidence. | Workflow metadata, compatibility evidence, canonical result | Authorized execution input and shared policies | Router dispatch after admission; target workflow contract and schemas | Slugger owns generation/validation; control plane owns admission. Explicit immutable capability pin plus separately governed current activation. |
| RI-03 `consulting-playbook` | Consulting knowledge source and optional execution target. Bidirectional if producing work. | Canonical proposed/approved work through portfolio path; compatibility evidence and results | Execution input, shared contracts, governance guidance | Approved work only; never local side-channel authorization | Playbook owner owns methods/content; portfolio owns approval; control plane owns interchange. |
| RI-04 future task producer | Adds governed sources without alternate execution. Inbound through approved portfolio identity. | Canonical approved task and provenance | Admission decision and diagnostics | Registered producer event; task contract | New producer owner plus control-plane approval; MINOR/MAJOR according to compatibility impact. |
| RI-05 future target | Adds independently operated execution domain. Outbound/inbound. | Registration request, owner, supported versions/modes, compatibility and result evidence | Authorized inputs, verification report, isolation state | Enablement only after review and read-only compatibility | Target owner executes; control plane owns registration and routing. |
| RI-MVP-01 result receiver | Canonical target-to-source return boundary. Inbound from targets; outbound to source owner. | Authenticated `execution-result/v2`, caller identity, delivery/correlation identity | Validated receipt, duplicate receipt, or classified rejection; idempotent source projection request | Target invokes organization-owned reusable workflow; ADR-010 | Target owns result creation/retry; `.github` owns validation/evidence/forwarding; `portfolio-tasks` owns issue projection. Immutable release pin. |
| RI-MVP-02 `.github` target adapter | Bounded execution target, isolated from the control plane. | Router-admitted canonical execution input only | Canonical result through RI-MVP-01 and, in implement mode only, one managed draft PR in `.github` | Planned `.github/workflows/codex-execute.yml`; requires an immutable reviewed revision before enablement | Target-only identity cannot approve, route, modify another repository, merge, release, deploy, or use control-plane credentials. |

## Per-interface operational contract

| Interface | Events | Failure modes | Recovery | Security | Expected evolution |
| --- | --- | --- | --- | --- | --- |
| RI-01 | Task approved, dispatch accepted/rejected, result reported | Missing approval, invalid payload, disabled/disallowed target, version mismatch, dispatch uncertainty, duplicate/ambiguous state | Correct source record; preserve immutable delivery fields; isolate if necessary; redeliver same logical task; reconcile GitHub evidence | Validate actor, approval, repository allowlist, ref, and payload; no Project-only authorization; scoped token | Richer approval attestations and lifecycle evidence without moving prioritization here |
| RI-02 | Verify/implement request, progress/result, draft PR | Target disabled, incompatible workflow, executor failure, duplicate branch/PR, result loss | Disable target; inspect marker/branch/PR; retain one valid draft; retry unchanged delivery; roll pin back | Protected environment, least privilege, no merge/deploy, target validates again | Additional factory capabilities behind new compatible versions |
| RI-03 | Governed intake, dispatch, result | Knowledge bypasses approval, target mismatch, confidential input, incompatible result | Return to portfolio approval; sanitize; disable execution role independently; retry only validated work | Separate knowledge access from execution credentials; data minimization | Consulting outputs may become structured task inputs through portfolio governance |
| RI-04 | Registration and approved dispatch | Unrecognized producer, competing source of truth, inadequate provenance | Reject; complete governance/onboarding; never infer approval | Producer identity allowlist and signed/immutable provenance where supported | Provider-neutral producer profiles |
| RI-05 | Registration, verification, enable/disable, dispatch/result | Missing owner, mutable ref, failed compatibility, unavailable target | Keep disabled; remediate locally; reverify; staged enablement/rollback | Dedicated environment and minimum repository scope; target isolation | Capability negotiation and attestations |

## Data and behavioral obligations

Producers shall supply an immutable task identity, `status: approved`, target identity, permitted task type, bounded instructions, and contract version. A v2 material edit requires a new task ID and new human approval; rich approval provenance remains source-local and undeclared fields are rejected. The control plane shall validate and authorize before projecting a canonical execution input without broadening scope. Targets shall validate again, distinguish read-only verification from implementation, use delivery identity for idempotent publication, produce a canonical result, and never automatically merge. Unknown, unavailable, or contradictory state produces no new execution.

Repository owners must approve interface changes affecting their domain. Breaking changes receive a new major payload or release boundary, additive changes require consumer acceptance before emission, and deprecations receive a published migration window and rollback point.

## Consumer conformance obligations

`CC-MVP-SOURCE` requires the source owner to retain revision-bound approval
provenance independently of labels, construct the canonical task, consume a
validated result once, and project its status, validation, and draft-PR link to
the source issue. `CC-MVP-TARGET` requires each of `.github`,
`portfolio-tasks`, `slugger`, and `consulting-playbook` to validate input and
authorization, implement explicit mode semantics, discover/reuse a managed
draft by delivery ID, emit `execution-result/v2`, and pass the organization
fixture matrix before enablement. These are organization-defined conformance
obligations, not claims that sibling repositories currently comply.

The canonical fixture release and expected-result manifest are owned here.
Consumers pin it immutably and run it against a repository-local adapter; they
do not need access to any sibling. Their owners must confirm local requirement
IDs, package/API surface, workflow mapping, permissions, and compatibility
evidence.
