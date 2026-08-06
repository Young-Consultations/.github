# Repository Interface Specification

## Contract rules

All production interfaces shall use immutable version references, canonical payload versions, explicit authorization, stable identity, sanitized failures, and owner-approved change control. Direction is relative to `.github`. Other repository behavior is inferred and must be confirmed during interface review.

## Interface inventory

| ID / repository | Purpose and direction | Inputs to `.github` | Outputs from `.github` | Trigger / contract | Ownership and versioning |
| --- | --- | --- | --- | --- | --- |
| RI-01 `portfolio-tasks` | Primary producer; also registered target. Bidirectional. | Approved task, issue identity, actor/approval provenance; execution result/compatibility evidence when targeted | Validation/routing result; canonical execution input; contract and adoption guidance | Explicit approved-task event invokes router; task, input, result schemas | Portfolio owner owns intent/approval and local execution; control plane owns interchange. Immutable release/payload pin. |
| RI-02 `slugger` | Software-factory execution target. Outbound dispatch; inbound evidence. | Workflow metadata, compatibility evidence, canonical result | Authorized execution input and shared policies | Router dispatch after admission; target workflow contract and schemas | Slugger owns generation/validation; control plane owns admission. Explicit enabled registry version and immutable pin. |
| RI-03 `consulting-playbook` | Consulting knowledge source and optional execution target. Bidirectional if producing work. | Canonical proposed/approved work through portfolio path; compatibility evidence and results | Execution input, shared contracts, governance guidance | Approved work only; never local side-channel authorization | Playbook owner owns methods/content; portfolio owns approval; control plane owns interchange. |
| RI-04 future task producer | Adds governed sources without alternate execution. Inbound through approved portfolio identity. | Canonical approved task and provenance | Admission decision and diagnostics | Registered producer event; task contract | New producer owner plus control-plane approval; MINOR/MAJOR according to compatibility impact. |
| RI-05 future target | Adds independently operated execution domain. Outbound/inbound. | Registration request, owner, supported versions/modes, compatibility and result evidence | Authorized inputs, verification report, isolation state | Enablement only after review and read-only compatibility | Target owner executes; control plane owns registration and routing. |

## Per-interface operational contract

| Interface | Events | Failure modes | Recovery | Security | Expected evolution |
| --- | --- | --- | --- | --- | --- |
| RI-01 | Task approved, dispatch accepted/rejected, result reported | Missing approval, invalid payload, disabled/disallowed target, version mismatch, dispatch uncertainty, duplicate/ambiguous state | Correct source record; preserve immutable delivery fields; isolate if necessary; redeliver same logical task; reconcile GitHub evidence | Validate actor, approval, repository allowlist, ref, and payload; no Project-only authorization; scoped token | Richer approval attestations and lifecycle evidence without moving prioritization here |
| RI-02 | Verify/implement request, progress/result, draft PR | Target disabled, incompatible workflow, executor failure, duplicate branch/PR, result loss | Disable target; inspect marker/branch/PR; retain one valid draft; retry unchanged delivery; roll pin back | Protected environment, least privilege, no merge/deploy, target validates again | Additional factory capabilities behind new compatible versions |
| RI-03 | Governed intake, dispatch, result | Knowledge bypasses approval, target mismatch, confidential input, incompatible result | Return to portfolio approval; sanitize; disable execution role independently; retry only validated work | Separate knowledge access from execution credentials; data minimization | Consulting outputs may become structured task inputs through portfolio governance |
| RI-04 | Registration and approved dispatch | Unrecognized producer, competing source of truth, inadequate provenance | Reject; complete governance/onboarding; never infer approval | Producer identity allowlist and signed/immutable provenance where supported | Provider-neutral producer profiles |
| RI-05 | Registration, verification, enable/disable, dispatch/result | Missing owner, mutable ref, failed compatibility, unavailable target | Keep disabled; remediate locally; reverify; staged enablement/rollback | Dedicated environment and minimum repository scope; target isolation | Capability negotiation and attestations |

## Data and behavioral obligations

Producers shall supply an immutable task identity, approved state and provenance, target identity, permitted task type, bounded instructions, contract version, and correlation data. The control plane shall validate and authorize before projecting a canonical execution input without broadening scope. Targets shall validate again, distinguish read-only verification from implementation, use delivery identity for idempotent publication, produce a canonical result, and never automatically merge. Unknown, unavailable, or contradictory state produces no new execution.

Repository owners must approve interface changes affecting their domain. Breaking changes receive a new major payload or release boundary, additive changes require consumer acceptance before emission, and deprecations receive a published migration window and rollback point.
