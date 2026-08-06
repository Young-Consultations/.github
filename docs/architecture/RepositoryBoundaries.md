# Repository Boundaries

## Owned by this repository

- Canonical task, execution-input, and execution-result semantics, schemas, examples, and shared validation distribution.
- Admission/routing interface, organization registry and routing policy.
- Stable identity, failure classification, correlation, execution-mode and compatibility rules.
- Read-only shared contract, routing, security-boundary, release, and target compatibility verification.
- Atomic control-plane release, adoption/deprecation/rollback guidance, and platform architecture.
- Control-plane operational diagnostics and evidence requirements.

## Explicitly not owned

- Product/portfolio intake truth, prioritization, readiness, or human approval decision.
- Target-specific requirements, implementation logic, AI prompts, source modification, testing, branch creation, or PR publication.
- Human review, merge, deployment, production operation, or automatic acceptance.
- Software-factory internals, consulting knowledge/methods, or external repositories' data models.
- GitHub platform implementation or external AI-provider implementation.

## Collaborators and contracts

| Collaborator | Owns | Required exchange |
| --- | --- | --- |
| Planning authority (`portfolio-tasks`) | Task record, governance, approval provenance, initiation | IF-01 canonical task and IF-02 invocation; consumes status/evidence |
| Target repository owner | Local permission, execution, idempotency, branch/draft PR, tests/evidence/result | IF-04/IF-06 input; IF-05 result; IF-08 conformance |
| Human approver/reviewer | Approval and consequential acceptance | Durable approval/review records |
| GitHub | Hosted identities and automation primitives | Authenticated platform interfaces |
| Security/operations | Credential, policy, incident and evidence governance | Controls, alerts, audits and recovery decisions |

## Data and lifecycle ownership

| Information/lifecycle | Authoritative owner |
| --- | --- |
| Task content, readiness, approval/withdrawal | Planning authority |
| Contract meaning/version support | Control plane |
| Registration enablement/isolation | Control plane with target/security approval |
| Route and dispatch attempt | Control plane |
| Execution progress, branch, PR, tests | Target repository |
| Review/merge decision | Authorized human/target governance |
| Release publication/deprecation | Control-plane release authority |

The control plane may retain references or projections needed for audit but does not become owner of source records. Material conflicts are resolved by consulting the authoritative owner; uncertainty blocks new side effects.

## Boundary enforcement

Permissions, separate credentials, closed schemas, exact repository identity, workflow allowlisting, immutable release pins, mode constraints, target-side validation, draft-only policy, and audit evidence make boundaries enforceable rather than aspirational.
