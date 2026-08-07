# Project Requirements Document

## Executive summary and product vision

Young Consultations requires a governed control plane that converts approved human intent into deterministic, authorized, traceable delivery requests while preserving human authority. This repository supplies the shared language, registration, routing policy, verification, and compatibility lifecycle. It is an organizational standard and integration subsystem—not a product factory, portfolio planner, or autonomous executor.

## Problem statement

Independent planning and execution repositories otherwise develop incompatible payloads, hidden routing knowledge, excessive credentials, ambiguous delivery identity, and unauditable automation. The organization needs one stable boundary that makes invalid or unauthorized work safe, makes outcomes reconstructable, and lets repositories evolve independently.

## Goals

| ID | Business goal | Strategic outcome |
| --- | --- | --- |
| BG-01 | Govern executable AI work | Only explicitly approved, registered, compatible work crosses the execution boundary. |
| BG-02 | Preserve human accountability | Automation proposes; humans review, merge, and authorize production use. |
| BG-03 | Enable interoperability | Participants exchange explicit, versioned, validated contracts. |
| BG-04 | Ensure traceability | Intent, approval, dispatch, attempts, evidence, result, and draft PR are correlated. |
| BG-05 | Limit blast radius | Least privilege, target isolation, and fail-closed behavior constrain failure. |
| BG-06 | Enable independent evolution | Immutable releases, compatibility evidence, deprecation, and rollback support deliberate adoption. |
| BG-07 | Improve delivery leverage | Clear, discoverable standards reduce onboarding and integration effort without weakening governance. |

## Scope

In scope are canonical task/input/result semantics; validation; registration and enablement policy; authorized deterministic routing; delivery identity and common failures; shared verification; release, compatibility, deprecation, recovery, and audit requirements; organization community-health and development-lifecycle standards where they support the control-plane mission; and documentation of ownership boundaries.

Out of scope are portfolio prioritization and approval decisions, product requirements, consulting methods, target implementation logic, direct target-source modification, AI model internals, automatic merge, production deployment authorization, and acting as an operational secrets store. Organization-wide templates are in scope only when established as governed standards; target-specific content stays local.

## Stakeholders and user types

| Stakeholder / user | Need | Accountability |
| --- | --- | --- |
| Organization owner | Risk and outcome visibility | Intent, policy limits, baseline approval |
| Engineering lead / architect | Coherent boundaries | Architecture and compatibility decisions |
| Portfolio manager / task producer | Predictable admission and feedback | Valid approved intent and priority outside this repository |
| Repository maintainer / integrator | Stable adoption contract | Local workflow, tests, permissions, pin, and recovery |
| Developer / contributor | Discoverable contribution path | Correct changes and evidence |
| Contract/release maintainer | Controlled evolution | Schemas, releases, migration, rollback |
| Security owner / auditor | Reconstructable authorization | Risk acceptance, review, audit |
| Bounded AI executor | Explicit authorized input | Operate only inside declared scope |
| Human reviewer | Clear proposed change and evidence | Consequential decisions and merge |

## Organization responsibilities

The organization owns identity and access governance, GitHub plan and platform availability, protected environments, credential issuance, policy exceptions, incident response, and assignment of maintainers. This repository owns standards and contracts; producers own intent and approval evidence; targets own execution and publication; humans own acceptance.

## Success criteria

The next delivery baseline is [the approved-issue-to-validated-draft-PR
MVP](../releases/next-mvp.md). Its functional success is one human-approved
revision routed to exactly one supported target, ending in one validated draft
PR and a canonical result correlated to the source issue. Continuous simulated
conformance across all four registered targets is required; one successful
dispatch is not sufficient.

1. 100% of admitted production dispatches reference approved canonical tasks and enabled registered targets.
2. 100% of boundary payloads validate against an explicitly supported version; invalid or uncertain inputs produce no dispatch.
3. Every canonical delivery can be reconstructed from source identity through terminal result and any draft PR.
4. Duplicate delivery produces at most one externally visible managed branch and open draft PR per delivery identity.
5. Every enabled target passes compatibility verification before enablement and release approval.
6. Automated paths have no permission to merge or authorize production deployment.
7. A documented rollback or target-isolation procedure is exercised for each release class.
8. A new integrator can locate the authoritative contract, adoption, verification, and recovery guidance from one index.
9. Normal cross-repository conformance CI exercises the complete interface with no Codex invocation or real branch/PR creation and rejects an incompatible consumer.

## Product principles

GitHub is the system of record; approval precedes execution; humans retain authority; contracts are explicit; ownership is singular; verification fails closed; publication is draft-only; automation never merges; interfaces contain no undocumented knowledge; security is least privilege; and every requirement traces to vision.

## Constraints and assumptions

Constraints: GitHub-hosted identities/events form the record; cross-repository access is explicitly authorized; shared policy remains implementation-independent; targets execute locally; releases are immutable; and sensitive diagnostics are sanitized. Assumptions: GitHub services and immutable references remain available; each target can implement the shared contract and idempotency obligations; organization owners can enforce repository settings; other repositories match the vision-level ownership model; and no database is required unless future audit retention exceeds GitHub capabilities.

## Risks

| Risk | Impact | Treatment |
| --- | --- | --- |
| Inferred consumer behavior is wrong | Broken integration | Validate interface specifications with each owner before approval. |
| Mutable workflow references | Non-reproducible execution | Require immutable production pins and inventory drift. |
| Credential compromise | Cross-repository impact | Least privilege, protected environments, rotation, and rapid disablement. |
| Duplicate/lost acknowledgement | Repeated publication | Stable delivery identity and target idempotency. |
| Contract drift | Inconsistent interpretation | One release unit and producer/consumer compatibility tests. |
| Governance overload | Slow adoption or bypass | Proportionate gates, usable templates, and measurable feedback. |
| GitHub outage/rate limit | Delayed work | Safe retries, no false success, operator-visible recovery. |
| AI prompt/data exposure | Confidentiality loss | Minimize, classify, sanitize, and approve provider use. |

## Future expansion

Potential, separately approved growth includes additional lifecycle contracts, more target repositories, provider-neutral executor profiles, policy-as-code evidence, organization metrics, signed attestations, federated identity, and retention exports. Expansion must retain the repository boundary and cannot imply autonomous approval, merge, or deployment.
