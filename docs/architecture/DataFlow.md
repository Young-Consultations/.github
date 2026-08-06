# Data Flow Design

## Data classes and boundaries

| Flow | Producer → consumer | Validation / transformation | Output |
| --- | --- | --- | --- |
| Task intake | Planning authority → Admission | Authenticate source; validate exact task contract and approval provenance | Admitted task or rejection |
| Policy resolution | Registry/release authority → Router | Validate snapshot/version/integrity; filter without broadening | One route or rejection |
| Input projection | Router domain → Delivery | Copy canonical semantics; add stable delivery/correlation identity and explicit mode | Execution input |
| Dispatch | Delivery adapter → Target workflow | Exact endpoint, scoped credential, canonical bytes | Attempt acknowledgement or uncertainty |
| Result | Target → Result interpreter | Validate contract/version/identity/status/evidence | Progress/terminal control-plane state |
| Operations | All components → telemetry/audit | Minimize, sanitize, classify, correlate | Metrics/logs/traces/evidence links |

## Command and event flow

Commands express requested actions: `AdmitTask`, `RouteDelivery`, `DispatchDelivery`, `ReconcileDelivery`, `VerifyTarget`, and `PublishRelease`. Facts may be recorded as `TaskAdmitted`, `RouteRejected`, `DispatchAttempted`, `DispatchAcknowledged`, `DeliveryUncertain`, `ResultAccepted`, `TargetIsolated`, and `ReleasePublished`. Names describe conceptual semantics; no messaging technology is required.

```mermaid
flowchart TD
  U[Untrusted task envelope] --> C[Contract validation]
  C -->|invalid| X[Classified rejection]
  C --> P[Approval provenance validation]
  P -->|invalid/stale| X
  P --> Q[Policy snapshot query]
  Q -->|zero/multiple/incompatible| X
  Q --> I[Canonical projection]
  I --> L[Per-delivery concurrency control]
  L --> G[GitHub dispatch boundary]
  G -->|acknowledged| W[Await/reconcile target result]
  G -->|timeout/unknown| R[Reconcile before retry]
  W --> Y[Validate result and evidence]
  Y -->|consistent| S[Record progress/terminal state]
  Y -->|invalid| Z[Quarantine + operator action]
  R --> W
```

## At-least-once redelivery

```mermaid
flowchart LR
  A[Same delivery ID + immutable input] --> B{Existing managed effect?}
  B -- none --> C[Create deterministic branch/draft PR]
  B -- one matching --> D[Return duplicate-reused]
  B -- conflicting/unknown --> E[Return ambiguous-rejected]
  C --> F{Create race?}
  F -- yes --> B
  F -- no --> G[Canonical result]
```

This target obligation yields exactly-once externally visible publication effects, not exactly-once AI execution.

## Data handling

Payloads contain only the minimum authorized engineering context and no secrets or prohibited personal/confidential data. Logs avoid raw payloads by default. Artifacts carry classification, owner, retention, and deletion policy. Integrity is protected by immutable GitHub identity and, where supported, digests/signatures. Repository boundaries are crossed only through interfaces catalogued in [Interface Architecture](InterfaceArchitecture.md).
