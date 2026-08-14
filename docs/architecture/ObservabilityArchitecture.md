# Observability Architecture

## Objectives

Operators must determine what was requested, why it was admitted/rejected, where it was routed, what attempts occurred, whether side effects may exist, what authoritative evidence says, and the safe next action. Observability never substitutes for authorization or target evidence.

## Signal model

| Signal | Required concepts |
| --- | --- |
| Structured logs | Timestamp, component/use case, release/registry/contract version, task/delivery/correlation/attempt IDs when valid, decision code, target, mode, retryability, owner; no secrets/raw payload by default. |
| Metrics | Admission/routing counts and latency; rejection/failure by stable category; dispatch acknowledgement/uncertainty; pending age; retry/reuse/ambiguity; target compatibility state (`pass`, `fail`, `not-evaluated`) and evidence identity; release adoption; queue/concurrency; redaction/security alerts. |
| Traces | Planning invocation → validation → policy decision → dispatch attempt → target/result reconciliation, linked across asynchronous boundaries by delivery/correlation identity. |
| Health | Contract/resource integrity, registry/release coherence, GitHub dependency/rate state, dispatch capability, result-channel lag, per-target compatibility/isolation, telemetry pipeline health. |
| Audit evidence | Actor, source/approval reference, immutable policy/release, decision, permission context, attempts, canonical outcome/evidence, draft PR and human review. |

## Service indicators and alerts

- Admission/routing availability and p95 processing latency (monthly, at least 30 events before percentile claims).
- Ratio and age of uncertain/pending deliveries; success without valid evidence must remain zero.
- Duplicate-reuse and ambiguous-rejection rates by target.
- Compatibility freshness and enabled-target failures.
- Secret/security-policy canary findings and telemetry gaps.

Alert on SLO breach, invalid release/registry, prolonged uncertainty, evidence conflict, unauthorized attempts, repeated target failure, unexpected non-draft publication, or sensitive-data detection. Alerts name severity, affected delivery/target, owner, side-effect uncertainty and runbook action.

## Diagnostics and privacy

User-facing diagnostics provide stable code, safe summary, correlation identity, side-effect status, owner and remediation. Detailed evidence is access-controlled and retention-bound. Redaction occurs before emission; access to logs/artifacts is audited. Telemetry failures are observable through independent health checks and never cause fail-open routing.
