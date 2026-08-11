# Integration Architecture

## Classification

**Known** is evidenced by this repository's vision/requirements/contracts. **Assumed** is a necessary design premise requiring validation. **Unknown** must not be converted into implementation detail without an approved decision.

| Integration | Classification | Contractual expectation |
| --- | --- | --- |
| GitHub repositories, Actions and API | Known dependency | Durable identities, workflow hosting and dispatch; external output remains untrusted; platform outages/rate limits are classified. |
| `portfolio-tasks` | Known boundary | Owns backlog, prioritization, approval state and initiation; supplies a canonical task and valid human approval provenance. Internal schema/workflow is not defined here. |
| Registered target repositories | Known boundary | Consume exact execution-input version, enforce local authorization/idempotency, execute verify or implement, publish at most one managed draft PR, emit canonical result. |
| `slugger` | Known responsibility boundary | May be a task source/target and owns software-factory generation/validation. No internal API or service design is assumed. |
| `consulting-playbook` | Known responsibility boundary | May produce governed portfolio work and owns consulting knowledge. No internal knowledge model is assumed. |
| AI provider/executor | Known conceptual dependency, target-owned | Used only during implement mode; receives minimized non-secret content; can propose but not approve/merge/deploy. Provider API is unknown. |
| Identity/secret/signing/scanning services | Assumed organization capabilities | Must provide least-privilege identity, protected secrets, integrity and security evidence where policy requires. Products and topology are unknown. |
| Result callback/event channel | Unknown | Must deliver IF-05 with authentication, integrity, correlation and at-least-once-safe behavior; transport awaits decision. |

## Synchronization and messaging

Registry and release policy are immutable snapshots for the duration of a decision. Task dispatch is asynchronous and at least once. There is no distributed transaction across planning, control plane, GitHub, and target. The target reports progress/terminal facts; the control plane reconciles them with delivery history. Ordering is guaranteed only within a delivery state machine; consumers must tolerate duplicate facts and delayed delivery.

## Workflow boundaries

1. Planning authorizes and invokes the router; it cannot select an unregistered endpoint.
2. The router validates, authorizes, selects and dispatches; it cannot inspect or alter target source.
3. The target verifies again, owns executor invocation and draft publication; it cannot reinterpret approval or change requested scope.
4. Human review is the only transition from proposal toward merge.

## Onboarding/offboarding

A target starts disabled, supplies owner/security/interface/idempotency evidence, passes compatibility and approval, then is enabled by a reviewed control-plane activation change. That operational change does not modify the immutable compatibility release or require consumer repinning. Isolation disables only that target. Offboarding revokes credentials/permissions, disables dispatch, preserves required audit/evidence, documents in-flight reconciliation, and follows retention/deletion policy.

## Integration failure policy

Malformed, incompatible, unauthorized, ambiguous, or integrity-invalid exchanges are non-retriable until corrected. Rate limits, platform unavailability, and bounded transport failures may be retried with the same payload/identity after reconciliation. Every integration failure names the responsible owner and safe next action without revealing secrets.
