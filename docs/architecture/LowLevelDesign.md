# Low-Level Design

## Logical modules

| Module | Public responsibility | Internal collaborators |
| --- | --- | --- |
| `ContractCatalog` | Resolve an exact supported artifact kind/version and validation rules | Contract resource port, integrity verifier |
| `BoundaryValidator` | Return all safe validation violations; never coerce required semantics | Catalog, format policy |
| `TaskAdmission` | Decide whether a task may enter routing | Validator, provenance verifier, clock/policy snapshot |
| `RegistryPolicy` | Validate registry and return eligible registrations | Registry repository, release policy |
| `RouteDecision` | Produce exactly one destination or classified rejection | Admission, registry policy |
| `ExecutionInputFactory` | Project admitted task to canonical input without semantic broadening | Identity policy, mode policy |
| `DeliveryCoordinator` | Serialize a delivery, invoke transport, classify acknowledgement | Dispatch port, telemetry |
| `ResultInterpreter` | Validate and correlate progress/terminal outcomes | Validator, evidence port |
| `RecoveryPlanner` | Recommend retry, reconcile, isolate, or escalate | Failure taxonomy, attempt history |
| `CompatibilityEvaluator` | Evaluate exact target dispatch/receiver interfaces, immutable tag/commit and digest-bound shared-oracle report in read-only mode | Workflow inspection/test ports |
| `ReleaseValidator` | Assert atomic manifest coherence and immutability | Catalog, registry, artifact digest port |

## Public use-case interfaces

```text
admit(taskEnvelope, requestedMode, policySnapshot) -> AdmissionDecision
route(admittedTask, registrySnapshot, releaseIdentity) -> RouteDecision
dispatch(executionInput, route, deliveryContext) -> DispatchOutcome
acceptResult(resultEnvelope, deliveryContext) -> ResultDecision
planRecovery(failure, deliveryHistory) -> RecoveryAction
verifyTarget(registration, releaseIdentity) -> CompatibilityReport
validateRelease(releaseCandidate) -> ReleaseDecision
```

Each operation returns a typed decision rather than throwing transport-specific errors across layers. Decisions include stable category/code, safe message, correlation and delivery identities when valid, retryability, owner, and evidence references.

## Internal interfaces (ports)

| Port | Contract |
| --- | --- |
| `ContractResourcePort` | Read immutable schema/example by artifact kind and major version; verify identity/integrity. |
| `ApprovalProvenancePort` | Establish authoritative task, actor, approval action, time, and freshness without inferring approval. |
| `RegistryPort` | Supply one immutable, version-identified registry snapshot. |
| `DispatchPort` | Deliver canonical bytes to the exact registered workflow and return acknowledgement/uncertainty. |
| `EvidencePort` | Resolve canonical result/evidence references without treating absence as success. |
| `AuditPort` | Append sanitized immutable decision and attempt facts. |
| `TelemetryPort` | Emit correlated logs, metrics, traces, and health signals. |
| `ClockPort` | Supply trusted time for freshness, expiry, latency, and retention decisions. |

## Core invariants

- `task_id` identifies authoritative work; `delivery_id` identifies one logical delivery; retry attempts never replace either.
- Immutable fields cannot change under an existing delivery identity.
- `correlation_id` supports observation and is not an idempotency key.
- A route has exactly one enabled target or is rejected.
- An enabled route has a governed adapter tag plus complete reviewed
  `TC-MVP-CI-001` evidence; disabled or unevaluated state is never compatibility
  success.
- Mode is explicit. Verify has no implementation/publication side effects; implement permits draft publication only.
- Dispatch input is canonical and schema-valid; target-specific prose is opaque bounded task content.
- Unknown outcome, lost acknowledgement, and absent result are never success.
- A release is usable only if its mutually dependent artifacts are coherent and immutable.
- Result journal trust comes only from the receiver's immutable control-plane
  policy; target input or secrets cannot change it.

## Extension points

Adapters may add a task source, transport, contract validator, evidence store, telemetry sink, or compatibility probe. Extension registration requires an owner, supported contract versions, security/data classification, failure semantics, conformance tests, and release impact. Domain rules and canonical meanings cannot be overridden by an adapter.

## Logical organization rules

Separate pure policy from I/O; keep serialization at boundaries; inject snapshots rather than reading mutable configuration during a decision; expose stable error codes; prefer total decision functions; retain fixtures for every supported major; and prohibit shared modules from parsing target-specific implementation details.
