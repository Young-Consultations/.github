# Component Design

Components are logical deployment-independent units. The platform architecture owner owns components in this repository; named external owners own their adapters and behavior.

| Component | Purpose / responsibilities | Inputs → outputs | Dependencies / lifecycle | Failure and scale |
| --- | --- | --- | --- | --- |
| Contract Authority | Define task, input, result semantics; versions; examples; compatibility | Change proposal → reviewed immutable contract release | Requirements, release authority; authored→reviewed→supported→deprecated→retired | Reject incoherence; cache immutable versions; never silently coerce |
| Validation Service | Validate shape, format, identity, and invariants at every boundary | Untrusted envelope + exact version → validation decision | Contract authority; invocation scoped | Aggregate safe violations; pure/stateless; horizontally scalable |
| Approval Admission | Prove authoritative task and explicit human approval are current | Task/provenance/mode → admitted task or rejection | Planning provenance contract, validation, policy | Fail closed on missing/stale/ambiguous provenance; stateless over snapshot |
| Registry Service | Govern target identity, owner, enablement, versions, modes, types, concurrency, publication/security policy | Registry snapshot/query → eligible registrations | Reviewed configuration, release identity | Invalid snapshot disables routing; read-heavy immutable cache |
| Router | Select exactly one target and project canonical input | Admitted task + registry/release → route/input/key | Registry, input factory | Zero/multiple match rejects; deterministic; partition by target/delivery |
| Delivery Coordinator | Dispatch through the registered endpoint and record attempt | Input + endpoint → acknowledged/uncertain/failed attempt | GitHub transport, secret broker, audit | Timeout is uncertain; reconcile before retry; bounded parallelism |
| Result Interpreter | Validate identity/status/evidence and determine authoritative state | Target result → accepted progress/terminal decision | Contract authority, evidence resolver, immutable journal-author policy | Invalid/inconsistent result or untrusted journal state is quarantined; scale per delivery |
| Recovery Coordinator | Turn classified failure/history into safe operator action | Failure + attempts → recovery plan | Audit/evidence, failure catalog | Never create side effect under uncertainty; serialize per delivery |
| Compatibility Verifier | Prove exact dispatch/receiver interfaces, immutable identity, permissions, modes, invalid cases, idempotency and the complete shared oracle before enablement | Registration/release → digest-bound durable report | Read-only target access/test harness | Disabled or missing evidence is not PASS; failure blocks enablement/release; parallel by target, rate limited |
| Release Authority | Bind contracts, package, router, registry format, checks and rollback | Candidate artifacts → immutable manifest/release decision | Review/signing/artifact integrity | Any mismatch blocks publication; single governed release transaction |
| Telemetry & Audit | Provide correlated operational and compliance visibility | Decisions/events → logs, metrics, traces, evidence links | Sanitizer, retention/access policy | Telemetry failure must not authorize work; buffer/drop safely and alert |

## Component interaction rules

No component bypasses validation to reach delivery. Only the Delivery Coordinator holds dispatch capability. Only Approval Admission may establish admissibility, but it does not grant target execution permission. Only target-owned systems create branch/PR evidence. Release artifacts are consumed by exact immutable identity. Audit records contain facts and references, not credentials or unrestricted payload copies.

## Ownership expectations

Contract, registry, router, compatibility, release, and platform operations require accountable maintainers and independent reviewers for governed changes. The planning owner remains accountable for task/approval truth. Each registered target owner remains accountable for local permissions, executor behavior, idempotency, evidence, and draft-only publication.
