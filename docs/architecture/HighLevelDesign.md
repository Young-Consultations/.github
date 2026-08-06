# High-Level Design

## Context and decomposition

```mermaid
C4Context
  title AI-SDLC control-plane context
  Person(human, "Human approver/reviewer", "Approves intent and reviews proposals")
  System(planning, "Authoritative planning repository", "Owns task and approval provenance")
  System(control, "Young-Consultations/.github", "Validates, authorizes, routes, verifies, releases")
  System(target, "Registered target repository", "Executes bounded work and reports outcomes")
  System(github, "GitHub platform", "Identity, records, workflows, delivery, artifacts")
  Rel(human, planning, "Creates and approves task")
  Rel(planning, control, "Canonical task + mode")
  Rel(control, target, "Canonical execution input")
  Rel(target, control, "Canonical result/evidence reference")
  Rel(human, target, "Reviews and may merge draft PR")
  Rel(control, github, "Uses governed platform services")
```

## Architectural layers

```mermaid
flowchart TB
  I[Interfaces\nReusable workflow · CLI · library · release artifacts]
  A[Application orchestration\nAdmit · Route · Dispatch · Reconcile · Verify · Release]
  D[Domain policy\nContracts · Identity · Approval · Registration · Decisions · Outcomes]
  P[Ports\nTask source · Policy store · Transport · Evidence · Clock · Telemetry]
  X[Infrastructure adapters\nGitHub · JSON Schema · files/package resources · workflow runtime]
  I --> A --> D
  A --> P --> X
  X -. data .-> P
```

Dependencies point inward. Domain policy has no dependency on GitHub Actions, a filesystem layout, a programming language, or a schema-validation library.

## Subsystems and responsibilities

| Subsystem | Responsibility | Owns | Does not own |
| --- | --- | --- | --- |
| Contract governance | Define semantics and compatibility | Canonical contract definitions and examples | Repository-specific fields |
| Admission and authorization | Establish task validity and human approval provenance | Admission decision/evidence | Approval decision itself |
| Registration and routing | Resolve one eligible destination | Registry policy and route decision | Target implementation |
| Delivery coordination | Send unchanged canonical request safely | Dispatch attempt metadata | Transactional execution |
| Result and recovery | Validate, correlate, classify, reconcile | Canonical control-plane interpretation | Target evidence creation |
| Compatibility assurance | Verify integration without side effects | Conformance evidence | Production implementation |
| Release governance | Bind compatible artifacts immutably | Release manifest/lifecycle | Consumer deployment |
| Operations | Expose safe diagnostic state | Control-plane telemetry | GitHub platform internals |

## Primary information flow

```mermaid
flowchart LR
  T[Canonical approved task] --> V{Contract and provenance valid?}
  M[Explicit execution mode] --> V
  V -- no --> F[Sanitized rejection; no dispatch]
  V -- yes --> R{Exactly one enabled policy match?}
  P[Registry + release snapshot] --> R
  R -- no --> F
  R -- yes --> B[Build canonical execution input]
  B --> D[Dispatch to registered workflow]
  D --> E[Target-owned execution/evidence]
  E --> O[Validate and correlate canonical result]
  O --> A[Durable audit and operator status]
```

## Ownership and trust boundaries

Crossing from planning to control plane, configuration to policy core, control plane to GitHub transport, and target result to control plane requires validation. The control plane trusts no payload merely because it originated in the organization. Credential possession does not imply task approval. Target success is authoritative only when its identity, contract version, delivery identity, and evidence satisfy the result contract.

## External dependencies

- **GitHub identity, repositories, Actions, API, artifacts, issues, and pull requests:** known platform dependency; availability and delivery are not controlled here.
- **Planning repository:** contractually supplies authoritative task and approval provenance; internal representation is unknown.
- **Registered targets:** contractually consume inputs, enforce local authorization/idempotency, and emit results; internals are unknown.
- **AI executor/provider:** target-owned and optional for implement mode; no control-plane credentials or authority.
- **Schema/validation ecosystem:** replaceable implementation dependency constrained by the canonical JSON Schema dialect.

## Scale and availability model

Scale is primarily by independent deliveries and target partition. Per-target concurrency policy prevents overload; per-delivery serialization prevents duplicate publication without globally serializing unrelated work. Stateless decision services may scale horizontally when all instances use the same immutable release and registry snapshot. Durable GitHub records and target evidence support recovery after ephemeral workflow loss.
