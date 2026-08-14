# Software Architecture Overview

## Executive summary

`Young-Consultations/.github` is the organization AI-SDLC **control plane**. It
owns the shared language, admission and routing policy, compatibility lifecycle,
and verification evidence that allow an approved GitHub task to be delivered
safely to exactly one registered repository. It never performs target
implementation, merge, deployment, portfolio prioritization, or approval. This
architecture is approved for next-MVP implementation under the authority order
Vision → Requirements → Architecture → Implementation. The 2.3.1 recovery
decisions in ADR-012–014 are part of that approved design; implementation
evidence cannot silently weaken them.

## Architectural vision and goals

The platform turns approved human intent into a deterministic, auditable execution request and a canonical outcome while preserving human merge authority. It shall:

1. admit only authoritative, explicitly approved work;
2. fail closed on invalid identity, authorization, policy, or compatibility;
3. isolate repositories behind versioned contracts and explicit registration;
4. support at-least-once transport with exactly-once externally visible publication effects per delivery identity;
5. make every decision and recovery action explainable without exposing sensitive data;
6. release interdependent control-plane artifacts as an immutable compatibility unit.

## Design principles

| Principle | Architectural consequence |
| --- | --- |
| Human authority | Automation may route and propose; it cannot approve, merge, or deploy. |
| Contract first | Closed, versioned canonical messages are validated at every trust boundary. |
| Clean boundaries | Domain policy is independent of workflow, GitHub transport, files, and validator technology. |
| Least privilege | Read by default; dispatch credentials are short-lived, scoped, and isolated to dispatch. |
| Determinism | Same authoritative task, mode, policy release, and registry version produce the same decision. |
| Fail closed | Unknown, ambiguous, stale, or incompatible state creates no execution side effect. |
| Evidence over inference | Missing target evidence is pending or failure, never success. |
| Evolution by release | Router, contracts, registry format, validator, verification, and manifest move together. |
| AI-safe development | Structured context, explicit invariants, stable terminology, and machine-checkable contracts bound agents. |

## Guiding constraints

- GitHub is the durable system of record and workflow host.
- Repository communication occurs only through documented, versioned interfaces.
- Target repositories own execution and publication idempotency.
- Production implementation produces draft pull requests only.
- Verification mode is read-only and cannot invoke an implementation agent.
- Automatic merge and direct default-branch mutation are prohibited.
- External repository internals are unknown; only their obligations are defined here.

## Quality attributes

| Attribute | Required design response |
| --- | --- |
| Security | Explicit trust boundaries, provenance checks, allowlisting, least privilege, redaction, immutable audit evidence. |
| Reliability | Stable delivery identity, non-cancelling concurrency, target idempotency, ambiguity rejection, reconciliation. |
| Maintainability | Ports/adapters, single owners, shared terminology, decision records, no repository-specific parsing in the core. |
| Testability | Pure policy decisions, contract fixtures, negative/boundary tests, read-only verification, transport fakes. |
| Performance | Validation and routing p95 ≤60 seconds excluding platform queue and target execution. |
| Availability | 99.5% monthly admission/routing target, visible degraded state, target isolation. |
| Observability | Correlated structured decisions, metrics, evidence references, sanitized diagnostics. |
| Compatibility | Exact major-version selection, immutable historical artifacts, coordinated additive emission. |
| Accessibility/usability | Actionable status and recovery messages; no status conveyed by color alone. |

## Architectural style

A policy-centric **clean architecture** with ports and adapters is used. The domain contains identities, contracts, registration, admission, routing, and outcome semantics. Application services orchestrate use cases. Interface adapters translate workflow/CLI/library calls. Infrastructure adapters access GitHub, schema resources, registry snapshots, release metadata, and telemetry. The normal interaction is synchronous admission followed by asynchronous at-least-once delivery and result reporting.

## System and repository responsibilities

The system defines canonical tasks, execution inputs/results, approval admission, deterministic target selection, common failure taxonomy, compatibility verification, and release governance. This repository owns those control-plane definitions and router behavior. Task authoring/approval belongs to the planning authority; implementation, branch/PR handling, and authoritative execution evidence belong to each target. See [Repository Boundaries](RepositoryBoundaries.md).

## Major components

1. **Contract authority** — canonical schemas, examples, version rules, validator distribution.
2. **Admission service** — validates task, approval provenance, requested mode, and invariants.
3. **Registry and policy service** — resolves an immutable target policy snapshot.
4. **Routing service** — builds one canonical execution input and deterministic concurrency key.
5. **Dispatch adapter** — performs the sole authorized cross-repository delivery.
6. **Outcome/evidence service** — validates and correlates canonical results; never invents success.
7. **Compatibility verifier** — read-only producer/router/target conformance checks.
8. **Release authority** — publishes and validates an atomic compatibility manifest.
9. **Operational telemetry** — sanitized logs, metrics, traces, diagnostics, and audit links.

## Architectural decisions

Normative decisions include canonical closed contracts, target-owned execution, at-least-once delivery with target idempotency, explicit modes, clean separation of policy and transport, immutable compatibility releases, and fail-closed authorization. Rationale and alternatives are recorded in [ADR](ADR.md).

## Risks

| Risk | Treatment |
| --- | --- |
| GitHub delivery acknowledgement is lost | Preserve immutable payload/delivery identity; reconcile before retry. |
| Registry drift or over-broad permissions | Schema/policy gate, reviewed enablement, pinned release, periodic audit. |
| Approval semantics remain externally underspecified | Admission adapter must validate an approved provenance contract; block until confirmed. |
| Target violates idempotency | Keep disabled until concurrency/redelivery compatibility evidence passes. |
| Sensitive content enters payloads/logs | Classification, minimization, schema constraints, scanning, redaction, restricted retention. |
| Mixed release versions | Atomic manifest and exact pins; no movable production reference. |
| External platform outage/rate limiting | Classified retriable state, backoff, degraded health, no false success. |

## Technical-debt assessment

The requirements gap analysis identifies governance capabilities beyond the current implementation. Architectural debt includes incomplete approval-provenance admission, incomplete authoritative result ingestion/reconciliation, incomplete operational SLO telemetry, absence of a formal registry schema/owner fields, incomplete signing/attestation, and missing organization standards distribution. These are gaps, not permission to weaken current guardrails. Delivery should prioritize authorization and evidence integrity, then lifecycle/observability, then usability and extension.

## Future evolution strategy

Evolve through capability slices mapped to requirements and compatibility releases. Add new contract majors alongside supported versions; isolate version translators at adapters, never in the domain model. Introduce alternative transports or validators only behind ports. Enable targets independently after read-only compatibility and security approval. Retire versions only after measured adoption, notice, migration evidence, and a tested rollback. New AI providers, task sources, and result consumers must not gain approval, routing-policy, merge, or deployment authority.
