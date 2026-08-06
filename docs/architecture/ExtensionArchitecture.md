# Extension Architecture

## Extension philosophy

Extend through explicit contracts and ports, never undocumented cross-repository knowledge or target-specific conditionals in shared policy. Extensions cannot override human approval, fail-closed validation, deterministic routing, draft-only publication, identity, evidence, or automatic-merge prohibitions.

## Extension points

| Extension | Required contract | Admission criteria |
| --- | --- | --- |
| New target repository | Registration + execution-input/result + target workflow + idempotency/evidence obligations | Named owner, least privilege, supported release/modes/types, read-only compatibility, security approval, disabled-first rollout |
| New task source | Canonical task producer + authoritative approval provenance | Human authority, identity/integrity, minimization, negative admission tests |
| New transport | Dispatch port | Authenticated exact endpoint, at-least-once semantics documented, uncertainty/reconciliation, rate/timeout behavior |
| New result channel | Result/evidence port | Authenticated integrity, correlation, duplicate/order behavior, retention/access, no false success |
| New contract major | Contract catalog adapter/version strategy | Vision/requirement trace, migration/support/deprecation, fixtures, producer/router/consumer compatibility |
| Validator/runtime | Validation port | Standards-conformant exact results, format checking, offline reproducibility, conformance corpus |
| Telemetry sink | Telemetry/audit port | Redaction, access/retention, delivery behavior, outage isolation |
| AI provider/executor | Target-owned execution adapter only | Data minimization, no secrets/control-plane credentials, recorded identity where available, proposal-only authority |

## Capability negotiation

Negotiation is policy selection from declared supported versions/capabilities, not runtime guessing. Producers emit only after all relevant consumers accept an additive change. Zero or multiple compatible selections fail closed. A future plugin manifest must name identity, owner, version, capabilities, permissions, data classes, interface versions, failure semantics, test suite and support lifecycle.

## Customization boundaries

Targets may customize implementation instructions, local tests, branch naming details consistent with deterministic delivery ownership, and evidence generation. They may not redefine canonical status/mode meanings, accept unauthorized scope, publish non-draft changes, or weaken delivery identity. Task sources may enrich intent only within the canonical contract and approval boundary.

## Future capability path

Potential transports, policy stores, event streams, evidence attestations, additional executors, and organization standards distribution should be introduced as replaceable adapters. Each change follows vision → requirement → ADR → contract/component/interface → tests → atomic release, with rollback and target-by-target adoption.
