# Architecture Traceability Matrix

## Method

Architecture identifiers are approved design obligations for next-MVP
implementation. Future implementation work shall add repository path/service,
test ID, release and operational evidence columns; a code location alone is not
proof. The approved vision and requirements baseline remain higher authority.
`V-FLOW`, `V-GUARD`, `V-RESP`, `V-EVOL`, `V-PRIN`, and `V-NRESP` are the
requirement baseline's vision themes.

## End-to-end trace

| Vision / business goal | Requirements | Architecture obligation | Components | Interfaces | Future implementation and proof |
| --- | --- | --- | --- | --- | --- |
| V-RESP/V-PRIN; BG-03 consistent shared language | GH-FR-001–003, GH-NFR-004, GH-QR-002/006 | ARC-CONTRACT: exact closed versioned contracts and inward policy | Contract Authority, Validation | IF-01, IF-04, IF-05, IF-07, IF-09 | Schemas/catalog/adapters; positive, negative, format, drift and major-version tests |
| V-FLOW/V-GUARD; BG-01 approved work only | GH-FR-002, GH-FR-005/006, GH-FR-010, GH-QR-004 | ARC-ADMISSION: prove human approval and deterministic single route | Approval Admission, Registry, Router | IF-01–04 | Provenance adapter/policy decisions; stale/forged/zero/multiple-match tests |
| V-NRESP/V-GUARD; BG-02 human authority | GH-FR-007/010, GH-ER-003, GH-SR-001/005 | ARC-BOUNDARY: target-owned execution, draft proposal, no merge/deploy | Router, Delivery; external Target | IF-02, IF-04, IF-06, IF-11 | Permission/static/E2E mode tests and protected human review evidence |
| V-RESP; BG-04 traceable reliable delivery | GH-FR-008/009/011/012, GH-NFR-002, GH-QR-007 | ARC-DELIVERY: stable identity, at-least-once delivery, evidence outcomes | Delivery, Result, Recovery | IF-04–06, IF-10 | Concurrency/redelivery/lost-ack/result reconciliation harness |
| V-GUARD; BG-05 safe operation | GH-FR-002/004/012/015, GH-SR-001–006, GH-ER-001–004 | ARC-SECURITY: zero trust, least privilege, minimization, isolation | All; Security/Telemetry | All external interfaces | Threat model, permission diff, secret canary, scanning, audit and isolation exercises |
| V-EVOL; BG-06 controlled evolution | GH-FR-003/013–015, GH-NFR-004, GH-QR-003/005 | ARC-RELEASE: compatibility gate and immutable atomic lifecycle | Compatibility Verifier, Release Authority | IF-08, IF-09 | Manifest/digest/signature checks, adoption/deprecation and rollback exercise |
| V-PRIN/V-FLOW; BG-07 usable governance | GH-FR-016, GH-NFR-001/003/005/006, GH-UX-003–008 | ARC-OPS-UX: discoverable, observable, accessible, actionable control plane | Telemetry, all interface adapters | IF-07–11 | SLI dashboards, link/content/accessibility/usability and recovery tests |
| V-GUARD/V-RESP; BG-03/BG-05 | GH-FR-013, GH-QR-001/007 | ARC-VERIFY: read-only compatibility before enablement/release | Compatibility Verifier | IF-08 | Producer/router/target invalid-case, verify-mode and idempotency reports |
| V-FLOW/V-GUARD; BG-01/BG-02/BG-04 | GH-FR-005/017 | ARC-MVP-APPROVAL: v2 approval admission precedes queue projection and material edits require a new task ID | Source Approval, Admission | RI-01, IF-01 | `TC-FR-017`, `TC-MVP-CI-001`; stale, withdrawn, edited and label-projection cases |
| V-RESP/V-GUARD; BG-03/BG-04/BG-05 | GH-FR-008/011/012/018 | ARC-MVP-RESULT: reusable authenticated receiver validates, deduplicates and projects results using only immutable control-plane journal-author trust | Target Result, Result Receiver, Source Projection, Reconciliation | RI-MVP-01, IF-05/06 | ADR-010/013; `TC-FR-018`, `TC-MVP-CI-001`, `TC-MVP-E2E-001`; target-supplied-policy, duplicate/missing/ambiguous cases |
| V-RESP/V-EVOL; BG-01/BG-03/BG-04/BG-06 | GH-FR-013–015, GH-QR-008 | ARC-MVP-CONFORMANCE: exact two-input dispatch plus one authoritative fixture oracle validates all four immutable target adapters without production effects; evidence uses a non-recursive file pin plus separate tag/commit/report bindings; disabled is not PASS | Fixture Authority, Compatibility Verifier, Conformance Reporter | IF-06/08/09, RI-01–RI-03, RI-MVP-01 | ADR-012/014/015; digest-bound `TC-MVP-CI-001` reports; incompatible/mutable/disabled/self-referential canaries; separately gated `TC-MVP-E2E-001` |
| V-FLOW/V-GUARD/V-RESP; BG-01/BG-02/BG-04/BG-05 | GH-FR-005/007–012/017–018, GH-QR-008 | ARC-MVP-E2E: one acceptance architecture exposes SIM and REAL only at explicit effect/provider boundaries; SIM runs the exact immutable enabled-target adapter with deterministic fake effects, while REAL preserves the source-owned human approval trigger and deployed router/target/receiver path | Source Approval, Router, Target Adapter, Execution Provider, Result Receiver, Source Projection | RI-01–RI-03, RI-MVP-01, IF-01/04–06 | `docs/acceptance/TC-MVP-E2E-001.md`; `scripts/run_tc_mvp_e2e_001.py`; `tests/test_tc_mvp_e2e_001.py`; `.github/workflows/tc-mvp-e2e-001.yml`; SIM zero-effect evidence plus later human-triggered REAL run and redelivery evidence |

## Requirement coverage index

| Requirement family | Primary architecture documents |
| --- | --- |
| GH-FR-001–003 | Software Architecture, Low-Level Design, Interface Architecture, ADR-002 |
| GH-FR-004–007 | High-Level Design, Repository Boundaries, Configuration, ADR-003/006/012/014 |
| GH-FR-008–012, GH-FR-017–018 | Domain Model, Data Flow, State Models, Error Handling, ADR-004/005/008–010/013 |
| GH-FR-013–016 | Integration, Deployment, Extension, ADR-007/014/015 |
| GH-NFR-* | Software Architecture quality attributes, Deployment, Observability, Security |
| GH-SR-* | Security Architecture, Configuration, Interface Architecture |
| GH-QR-* | Component/Low-Level Design, Observability, Release/compatibility decisions, next-MVP conformance architecture |
| GH-UX-* | Interface Architecture, Error Handling, Observability, repository documentation navigation |
| GH-ER-* | Integration and Security Architecture |

## Change-control rule

Every future change must cite at least one requirement, affected `ARC-*` obligation, component, interface and test/evidence artifact. Untraced implementation is not architecture-conformant. A conflict is resolved in the order Vision → Requirements → Architecture → Implementation, with the discrepancy documented rather than normalized into design.
