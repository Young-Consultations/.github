# Next-MVP path reconciliation

**Status:** Current implementation inventory reconciled to the approved next-MVP baseline on 2026-08-11.

This inventory applies the authority order in [`AI_CONTEXT.md`](../AI_CONTEXT.md). It does not assert sibling-repository conformance or enable execution. The supported contract family is only `task-contract/v2`, `execution-input/v2`, and `execution-result/v2`.

## Migration decisions

| Candidate | Decision | Current disposition | Authoritative reason |
| --- | --- | --- | --- |
| Root v2 schemas, examples, validator, and CLI validation commands | KEEP | Sole local contract and validation path | GH-FR-001/002 and ADR-002 require canonical closed contracts and exact boundary validation. |
| Local `contracts/v1/` and packaged `contracts/v1/` copies | REMOVE | Deleted; history retains evidence | The next-MVP interface baseline selects only v2, and the pre-production baseline approves no backward-compatibility path. |
| Built-in alias normalization and caller-supplied migration mappings | REMOVE | Deleted; validation now checks the supplied payload exactly | The closed v2 interface forbids inference, renaming, coercion, and compatibility adapters. |
| GitHub-issue task builder, builder CLI command, fixture, and tests | REMOVE | Deleted | Portfolio task creation and approval projection belong to `portfolio-tasks`; this control plane owns validation and admission, not source-task authoring. |
| Organization router | KEEP | Sole dispatch boundary | GH-FR-006/007 and ADR-003 require deterministic control-plane routing to target-owned execution. |
| Target `codex-execute.yml` implementations | CONVERGE | `.github/workflows/codex-execute.yml` is the sole `.github` target adapter; sibling entries remain disabled external dependencies | Targets own implementation and draft publication. The local adapter remains disabled pending owner-approved immutable revision, credentials, and enablement. |
| Result-receiver workflow interface | MODIFY | Retained as the sole declared receiver and explicitly fail closed | GH-FR-018 and ADR-010 require one reusable receiver. Durable bindings, deduplication, evidence storage, and source projection are not yet implemented, so accepting results would be unsafe. |
| Router smoke and compatibility workflows | KEEP | Read-only verification paths only | GH-FR-013 and GH-QR-008 require deterministic, no-Codex compatibility evidence; these workflows do not provide an alternate executor or publisher. |
| Consulting migration workflow, shell driver, patches, report, and their tests | REMOVE | Deleted | Cross-repository consulting asset modification belongs to the affected target owners and is outside the AI-SDLC control-plane next-MVP responsibilities. |
| Mutable target adapter references in the registry | DEFER | Recorded only for disabled registrations; none is supported for dispatch | The interface baseline records these as configuration rather than compatibility pins. GH-NFR-009, GH-SR-002, and the deployment gate require owner-approved immutable revisions before enablement. |
| Historical release and ADR narrative | KEEP | Retained as governance/history, not an executable interface | GH-FR-014/015 require immutable lifecycle, deprecation, rollback, and decision evidence. |

## Single supported path

1. A source owner supplies one approved closed v2 task.
2. `codex-router.yml` validates it, selects exactly one compatible capability entry, and requires current activation before dispatch.
3. The selected repository's target-owned adapter revalidates one canonical v2 input and either verifies read-only or implements draft-only.
4. The target returns one canonical v2 result through `codex-result-receiver.yml`.
5. The receiver validates and idempotently forwards one projection to the source owner.

There is no local task-authoring adapter, v1 validator, alias normalizer, alternate router, control-plane executor, cross-repository publisher, or migration workflow.

## External dependencies and safe stopping point

Execution remains disabled because target owners have not supplied the documented immutable adapter revisions and conformance reports. The organization receiver now uses source-owned admission/receipt journal records and an authenticated source projection dispatch, but the result-only credential, retention period, source consumer, and `ai-sdlc-v2.3.0` tag still require deployment/governance approval. This repository must not invent that evidence, enable a mutable adapter, or absorb target/source responsibilities.
