# Software Requirements Specification (SRS)

## 1. Introduction

### 1.1 Purpose and scope

This specification defines verifiable requirements for the `Young-Consultations/.github` AI-SDLC control plane. It follows ISO/IEC/IEEE 29148 concepts: stakeholder needs are refined into uniquely identified, necessary, feasible, implementation-independent requirements with bidirectional traceability. It specifies required behavior, not the current design.

### 1.2 Definitions and references

Controlled terms are in [the glossary](glossary.md). Normative context is the [vision](../VISION.md), [PRD](project-requirements.md), [repository context](repository-context.md), [repository interfaces](repository-interfaces.md), and [external interfaces](external-interfaces.md). The current schemas, registry, workflows, tests, and release guidance are informative current-state evidence only.

### 1.3 Overview

Sections 2–6 describe the product, requirements, and verification. Every requirement includes ID, priority, rationale, acceptance criteria (AC), source, verification method, and traceability. The [matrix](requirements-traceability.md) completes upstream and future-test traceability.

## 2. Overall description

### 2.1 Product perspective and functions

The subsystem sits between approved task producers and registered execution repositories. It manages canonical contracts; validates approval and payloads; registers and isolates targets; routes deterministically; correlates intent, attempts, and outcomes; defines idempotency and failure semantics; verifies compatibility; and governs immutable releases. It shares organization standards but performs no target implementation.

### 2.2 User classes

Organization owners approve policy; portfolio managers produce approved intent; maintainers integrate and release; target developers implement local execution; security owners administer trust; auditors inspect evidence; contributors use standards; human reviewers accept or reject proposed work; bounded AI executors consume only authorized inputs. Privilege and technical familiarity differ, so machine contracts and human diagnostics are both required.

### 2.3 Operating environment

The required behavior operates in GitHub organizations, repositories, Issues, pull requests, Actions, APIs, Releases, and protected environments; consumers may use heterogeneous operating systems and implementation languages. Contracts must remain platform-readable and implementation-neutral. GitHub outages, rate limits, event redelivery, and concurrent attempts are normal failure conditions.

### 2.4 Constraints, assumptions, dependencies

GitHub is the system of record; human approval precedes work; targets execute locally; publication is draft-only; humans merge and authorize production; production references are immutable; shared rules do not absorb target logic. Dependencies and unvalidated assumptions are catalogued in the repository and interface specifications. Where an assumption is unresolved, admission fails closed.

## 3. Functional requirements

### 3.1 Canonical contracts

**GH-FR-001 — Canonical language (Must).** The control plane shall define one canonical, implementation-neutral representation for approved tasks, execution inputs, and execution results. **Rationale:** prevents hidden bilateral formats. **AC:** each artifact has a unique type/version, required semantics, closed or explicitly extensible field policy, positive/negative examples, and named owner. **Source:** V-RESP, V-PRIN. **Verification:** inspection and schema conformance tests. **Trace:** BG-03; RR-contracts; `TC-FR-001`.

**GH-FR-002 — Boundary validation (Must).** Each producer, router, and consumer boundary shall validate identity, required semantics, format, invariant, and supported contract version before acting. **Rationale:** distrust across repositories. **AC:** missing, malformed, unknown, incompatible, or contradictory values produce no dispatch/publication and a classified sanitized failure. **Source:** V-GUARD. **Verification:** negative contract/integration tests. **Trace:** BG-01/BG-05; RR-validation; `TC-FR-002`.

**GH-FR-003 — Contract evolution (Must).** The control plane shall classify compatible and breaking changes and preserve supported version artifacts through migration. **Rationale:** independent evolution. **AC:** breaking changes use a new major boundary; additive emission waits for relevant consumers; support/deprecation dates and migration guidance are published. **Source:** V-EVOL. **Verification:** change-impact and compatibility tests. **Trace:** BG-03/BG-06; RR-lifecycle; `TC-FR-003`.

### 3.2 Registration, approval, and routing

**GH-FR-004 — Registration (Must).** The control plane shall maintain an authoritative registration model containing immutable target identity/capability semantics and separately governed mutable enablement state, including owner, workflow contract, supported versions/modes/task types, concurrency limits, publication policy, and security environment. **Rationale:** explicit trust. **AC:** unknown, disabled, incomplete, or incompatible entries cannot receive work. **Source:** V-RESP/V-GUARD. **Verification:** registry schema and negative routing tests. **Trace:** BG-01/BG-05; RR-registry; `TC-FR-004`.

**GH-FR-005 — Approval admission (Must).** The control plane shall admit executable work only when an authoritative GitHub task has explicit valid human approval provenance. **Rationale:** preserves human authority. **AC:** project-field changes, discussion text, AI output, labels without approved semantics, or absent/stale approval cannot independently authorize dispatch. **Source:** V-FLOW/V-GUARD. **Verification:** authorization scenario tests and audit. **Trace:** BG-01/BG-02; RR-routing; `TC-FR-005`.

**GH-FR-006 — Deterministic authorization (Must).** For an admitted task, the control plane shall select exactly one enabled target/workflow whose policy permits the repository, task type, mode, and contract version, without broadening requested scope. **Rationale:** predictable routing. **AC:** identical authoritative input and registry version yields the same selection; zero or multiple matches fail without dispatch. **Source:** V-RESP. **Verification:** decision-table tests. **Trace:** BG-01/BG-04; RR-routing; `TC-FR-006`.

**GH-FR-007 — Target-owned execution (Must).** The router shall deliver the canonical input to the registered target but shall not modify target source, interpret target-specific implementation content, merge, or deploy. **Rationale:** responsibility boundaries. **AC:** permission and behavior inspection shows no such capability. **Source:** V-NRESP/V-GUARD. **Verification:** static permission inspection and end-to-end test. **Trace:** BG-02/BG-05; RR-boundary; `TC-FR-007`.

### 3.3 Identity, modes, results, and recovery

**GH-FR-008 — Durable identity (Must).** Every delivery shall carry immutable task and delivery identities plus correlation sufficient to associate source intent, approval, dispatch attempts, target execution, result, branch, and draft PR. **Rationale:** audit and recovery. **AC:** every record resolves to one task/delivery; retries retain delivery identity and immutable fields; attempt identity, if present, does not replace it. **Source:** V-RESP. **Verification:** trace reconstruction and redelivery tests. **Trace:** BG-04; RR-correlation; `TC-FR-008`.

**GH-FR-009 — Observable uniqueness (Must).** The interface shall require target idempotency such that at-least-once delivery creates at most one managed deterministic branch and one open managed draft PR per delivery identity. **Rationale:** GitHub dispatch is not transactional. **AC:** sequential/concurrent duplicate tests reuse one valid draft or reject ambiguity; changed immutable fields under one identity fail. **Source:** V-RESP/V-GUARD. **Verification:** concurrency and redelivery harness. **Trace:** BG-04/BG-05; RR-idempotency; `TC-FR-009`.

**GH-FR-010 — Execution modes (Must).** Each request shall explicitly declare shared execution-mode semantics; verification is read-only and implementation can only propose changes as a draft PR. **Rationale:** prevents inferred authority. **AC:** verification invokes no AI implementation, branch, or PR; implementation cannot publish non-draft or merge. **Source:** V-FLOW/V-GUARD. **Verification:** mode integration tests. **Trace:** BG-01/BG-02; RR-modes; `TC-FR-010`.

**GH-FR-011 — Canonical outcomes (Must).** Targets shall report canonical progress or terminal outcomes containing identity, status, evidence references, and safe failure classification. **Rationale:** consistent interpretation. **AC:** success, verified, duplicate reuse, rejection, cancellation, and failure scenarios are distinguishable and schema-valid; absence is not success. **Source:** V-RESP. **Verification:** schema and scenario tests. **Trace:** BG-03/BG-04; RR-results; `TC-FR-011`.

**GH-FR-012 — Safe failure and recovery (Must).** The control plane shall define common failures and operator actions for validation, authorization, compatibility, delivery ambiguity, target unavailability, and evidence inconsistency. **Rationale:** prevent unsafe improvisation. **AC:** every class has stable code, sanitized message, retryability, owner, and recovery; uncertainty produces no new side effect. **Source:** V-PRIN/V-EVOL. **Verification:** fault injection and recovery exercise. **Trace:** BG-04/BG-05; RR-recovery; `TC-FR-012`.

### 3.4 Verification and lifecycle

**GH-FR-013 — Compatibility gate (Must).** An enabled target and a release shall pass read-only producer/router/target compatibility verification before production adoption. **Rationale:** independent but coherent evolution. **AC:** evidence covers interfaces, versions, required permissions, mode semantics, and invalid cases; failure prevents enablement/release. **Source:** V-RESP/V-EVOL. **Verification:** compatibility suite and approval record. **Trace:** BG-03/BG-06; RR-verification; `TC-FR-013`.

**GH-FR-014 — Atomic release unit (Must).** Interdependent router interface, schemas, validator, registry format, verification behavior, and release metadata shall be released as one immutable compatibility unit. **Rationale:** avoids mixed-version drift. **AC:** manifest enumerates versions/digests/targets and maps payload to release; published identity cannot move. **Source:** V-EVOL. **Verification:** release validation and tag integrity inspection. **Trace:** BG-06; RR-release; `TC-FR-014`.

**GH-FR-015 — Adoption, deprecation, rollback (Must).** The repository shall publish consumer adoption, support, deprecation, isolation, and rollback procedures. **Rationale:** controlled change. **AC:** each release identifies known-good rollback; removals follow approved notice/migration except documented emergency risk acceptance; one target can be disabled without affecting others. **Source:** V-EVOL. **Verification:** tabletop exercise and release review. **Trace:** BG-05/BG-06; RR-lifecycle; `TC-FR-015`.

**GH-FR-016 — Standards distribution (Should).** Organization-wide templates, policies, and lifecycle guidance owned here shall be discoverable, version-controlled, accessible, and clearly distinguish inherited defaults from mandatory controls. **Rationale:** usable governance. **AC:** artifact inventory names owner/scope/override policy and representative repository onboarding finds the applicable standard. **Source:** V-PRIN/V-RESP. **Verification:** documentation inspection and usability test. **Trace:** BG-07; RR-standards; `TC-FR-016`.

**GH-FR-017 — Revision-bound lifecycle authorization (Must).** For the v2 MVP, the organization shall route only a canonical task whose `status` is `approved`; `queued` is a post-admission source projection and is not accepted as fresh authorization. **Rationale:** the closed v2 task has no separate approval identity or revision digest, so queue presentation cannot substitute for its explicit authorization field. **AC:** a material edit receives a new `task_id` and fresh human approval; the router rejects proposed, queued, stale, withdrawn, or otherwise non-approved input; target and delivery remain bound to the admitted payload; cancellation prevents new effects and is best-effort in flight. **Source:** V-FLOW/V-GUARD; next-MVP objective. **Verification:** lifecycle decision-table and router authorization tests. **Trace:** BG-01/BG-02/BG-04; ADR-009; `TC-FR-017`, `TC-MVP-CI-001`.

**GH-FR-018 — Result return and reconciliation (Must).** Targets shall return canonical `execution-result/v2` through the authenticated organization result receiver, which shall validate identity/schema, deduplicate, retain evidence, and idempotently forward it to the source owner for issue correlation. **Rationale:** acknowledgement is not success and direct target issue writes violate least privilege. **AC:** valid, duplicate, delayed, missing, conflicting, malformed, and unauthorized results have deterministic outcomes; retries retain the delivery ID and immutable result payload; ambiguity creates no new side effect; the source projection includes execution status, validation status, and draft-PR link when required. **Source:** V-RESP/V-GUARD; next-MVP objective. **Verification:** result-return fault/replay harness and controlled E2E. **Trace:** BG-03/BG-04/BG-05; ADR-010; `TC-FR-018`, `TC-MVP-CI-001`, `TC-MVP-E2E-001`.

## 4. Nonfunctional requirements

**GH-NFR-001 — Performance (Should).** Control-plane validation and routing shall add no more than 60 seconds at the 95th percentile, excluding GitHub queue/target time, measured monthly over at least 30 events; smaller samples shall be reported without claiming the percentile. **Rationale:** governance should not obstruct flow. **AC:** metric and threshold breach alert exist. **Source:** V-FLOW. **Verification:** telemetry analysis/load test. **Trace:** BG-07; `TC-NFR-001`.

**GH-NFR-002 — Reliability (Must).** Accepted delivery shall never be reported as successful without authoritative target evidence, and retriable operations shall preserve immutable identity and payload. **AC:** injected lost acknowledgements/timeouts yield pending/failed state or idempotent retry, never false success. **Source:** V-PRIN. **Verification:** fault injection. **Trace:** BG-04/BG-05; `TC-NFR-002`.

**GH-NFR-003 — Availability (Should).** The control plane shall target 99.5% monthly availability for admission and routing, excluding documented GitHub-wide outages, with degraded state visible to operators. **AC:** SLI definition, measurement, and incident record exist. **Source:** V-FLOW. **Verification:** service-level review. **Trace:** BG-07; `TC-NFR-003`.

**GH-NFR-004 — Maintainability (Must).** Shared behavior shall have a named owner, modular responsibility, automated regression evidence, and current operator documentation. **AC:** change review can identify owner, affected requirements/interfaces/tests, and rollback. **Source:** V-PRIN. **Verification:** maintainability audit. **Trace:** BG-06/BG-07; `TC-NFR-004`.

**GH-NFR-005 — Extensibility (Should).** New producers, targets, task types, and providers shall be addable through explicit versioned capability contracts without embedding repository-specific execution logic in the control plane. **AC:** architecture scenario adds a hypothetical target without changing unrelated target semantics. **Source:** V-EVOL/V-GUARD. **Verification:** change scenario review. **Trace:** BG-03/BG-06; `TC-NFR-005`.

**GH-NFR-006 — Scalability (Should).** Routing shall enforce per-target concurrency and isolate load so one target cannot exhaust or block another; registry and verification shall support at least 100 targets without semantic change. **AC:** model/load test demonstrates isolation and deterministic selection. **Source:** V-RESP. **Verification:** load/architecture test. **Trace:** BG-05/BG-06; `TC-NFR-006`.

**GH-NFR-007 — Accessibility (Must).** Human-facing templates and documentation shall conform to WCAG 2.2 AA principles applicable to repository content, including semantic headings, descriptive links, text alternatives, keyboard-compatible forms, and no color-only meaning. **AC:** automated checks plus manual keyboard/screen-reader review find no critical violation. **Source:** V-FLOW. **Verification:** accessibility audit. **Trace:** BG-07; `TC-NFR-007`.

**GH-NFR-008 — Internationalization (Could).** Human-facing text shall use plain locale-neutral English, UTC/ISO 8601 machine timestamps, and avoid meaning encoded in date/number display formats, allowing later localization. **AC:** format and content review passes; identifiers remain language-neutral. **Source:** V-PRIN. **Verification:** inspection. **Trace:** BG-07; `TC-NFR-008`.

**GH-NFR-009 — Security (Must).** The subsystem shall enforce deny-by-default authorization, least privilege, boundary validation, immutable production dependencies, secret minimization, and separation of approval from execution. **AC:** threat model and permission tests show no unapproved execution, merge, secret disclosure, or cross-target escalation. **Source:** V-GUARD. **Verification:** threat modeling/security tests. **Trace:** BG-01/BG-02/BG-05; `TC-NFR-009`.

**GH-NFR-010 — Auditability (Must).** Authorization, policy/version decision, actor, input identity, dispatch attempts, result, evidence, exceptions, and release approvals shall be reconstructable for at least the organization-approved retention period. **AC:** sampled delivery/release reconstructs chronology and decision basis without relying on transient logs alone. **Source:** V-PRIN/V-RESP. **Verification:** audit reconstruction. **Trace:** BG-04; `TC-NFR-010`.

**GH-NFR-011 — Observability (Must).** Operations shall emit structured status and correlation for validation, routing, delivery, compatibility, and release gates with actionable owner-facing diagnostics. **AC:** dashboards or GitHub-native views expose success/failure/latency and alert on sustained or security-significant failure without sensitive data. **Source:** V-RESP. **Verification:** telemetry/log review. **Trace:** BG-04/BG-05; `TC-NFR-011`.

**GH-NFR-012 — Compliance (Must).** The repository shall maintain evidence of policy approvals, access reviews, dependency provenance, license obligations, data classification, retention, and exceptions required by applicable organization policy and law. **AC:** compliance mapping has owner, cadence, evidence link, and no unexplained mandatory-control gap. **Source:** V-GUARD. **Verification:** compliance audit. **Trace:** BG-05; `TC-NFR-012`.

**GH-NFR-013 — Governance (Must).** Normative assets shall have accountable owners, review cadence, protected change approval, exception expiry, and semantic baseline version. **AC:** unapproved changes cannot become authoritative; overdue reviews/exceptions are visible. **Source:** V-PRIN/V-EVOL. **Verification:** repository-rule and record inspection. **Trace:** BG-02/BG-06; `TC-NFR-013`.

**GH-NFR-014 — Developer experience (Should).** A new integrator shall locate authoritative guidance, validate an example, understand a failure, and identify support/rollback within 30 minutes without private knowledge. **AC:** representative usability test succeeds in time. **Source:** V-PRIN/V-FLOW. **Verification:** moderated onboarding test. **Trace:** BG-07; `TC-NFR-014`.

**GH-NFR-015 — Automation (Must).** Repetitive normative checks shall be automated, deterministic, rerunnable, and fail closed while retaining a human-readable remediation path. **AC:** clean runs are repeatable and injected invalid states fail before side effects. **Source:** V-PRIN. **Verification:** repeatability/negative tests. **Trace:** BG-01/BG-07; `TC-NFR-015`.

**GH-NFR-016 — Documentation (Must).** Documentation shall identify audience, owner, scope, prerequisites, version, normative status, examples, failure/recovery, and links without contradicting contracts. **AC:** documentation lint/link/accuracy review passes each release. **Source:** V-PRIN/V-EVOL. **Verification:** doc quality gate. **Trace:** BG-03/BG-07; `TC-NFR-016`.

**GH-NFR-017 — Versioning (Must).** Public contracts and compatibility units shall use documented semantic version rules, immutable release identifiers, integrity-verifiable artifacts, and machine-readable version discovery. **AC:** compatibility classification and version consistency gates reject drift or reused identity. **Source:** V-EVOL. **Verification:** release tests. **Trace:** BG-03/BG-06; `TC-NFR-017`.

## 5. Operational and security requirements

**GH-OR-001 — CI/CD gates (Must).** Protected changes shall pass contract, unit, integration, compatibility, security, documentation, and release-consistency checks applicable to their impact before merge/release. **AC:** required checks cannot be bypassed except by time-bound audited emergency procedure. **Source:** V-RESP/V-EVOL. **Verification:** ruleset and failure-path inspection. **Trace:** BG-05/BG-06; `TC-OR-001`.

**GH-OR-002 — Branches and review (Must).** Default branches shall reject direct changes and require current checks, resolved review, required code-owner/security approval for owned areas, and conversation resolution. **AC:** unauthorized/direct/stale-approval scenarios are blocked and exceptions logged. **Source:** V-FLOW/V-GUARD. **Verification:** settings test. **Trace:** BG-02/BG-05; `TC-OR-002`.

**GH-OR-003 — Repository configuration (Must).** Critical repository/ruleset/environment/Actions configuration shall be inventoried, least-privilege, periodically reviewed, and drift-detectable. **AC:** quarterly comparison identifies unauthorized variance and owner. **Source:** V-GUARD. **Verification:** configuration audit. **Trace:** BG-05/BG-06; `TC-OR-003`.

**GH-OR-004 — Issue lifecycle (Should).** Governed work shall have a durable issue identity, owner, readiness evidence, status, linked changes/results, and closure rationale. **AC:** sampled work traces from need through outcome; closed-without-delivery is distinguishable. **Source:** V-ORG/V-FLOW. **Verification:** workflow audit. **Trace:** BG-04/BG-07; `TC-OR-004`.

**GH-OR-005 — Release process (Must).** Releases shall originate from reviewed protected commits, pass all gates and consumer compatibility, publish notes/migration/security/rollback information, and never mutate a published identity. **AC:** release checklist and integrity validation pass; tag collision blocks publication. **Source:** V-EVOL. **Verification:** dry run and release audit. **Trace:** BG-06; `TC-OR-005`.

**GH-OR-006 — Workflow and template governance (Must).** Reusable workflows and organization templates shall declare interface, permissions, trust assumptions, owner, supported version, validation, and override policy. **AC:** inventory review finds no undocumented production workflow/template. **Source:** V-RESP/V-PRIN. **Verification:** static policy test. **Trace:** BG-03/BG-07; `TC-OR-006`.

**GH-OR-007 — Secrets and OIDC (Must).** Workflows shall prefer short-lived OIDC or GitHub App credentials; any secret shall be scoped to the minimum repository/environment/action, masked, rotated, access-reviewed, and absent from fork/untrusted contexts. **AC:** secret inventory has owner/rotation/consumers; log scanning and fork tests disclose none. **Source:** V-GUARD. **Verification:** permission, log, and credential audit. **Trace:** BG-05; `TC-OR-007`.

**GH-OR-008 — Organization policy enforcement (Must).** Mandatory organization controls shall be machine-verifiable where GitHub supports enforcement, with documented owner-approved, expiring exceptions. **AC:** nonconforming repository/configuration is visible and cannot silently claim compliance. **Source:** V-PRIN/V-GUARD. **Verification:** policy compliance scan. **Trace:** BG-05/BG-06; `TC-OR-008`.

**GH-SR-001 — Workflow permissions (Must).** Every job shall declare minimum permissions; write and cross-repository access shall be isolated to the smallest authorized job after validation and approval. **AC:** permission analyzer detects no implicit/excess scope and negative path has no write token. **Source:** V-GUARD. **Verification:** static/dynamic permission tests. **Trace:** BG-01/BG-05; `TC-SR-001`.

**GH-SR-002 — Artifact and supply-chain integrity (Must).** Production Actions, packages, schemas, and release artifacts shall be pinned immutably, provenance-verifiable, vulnerability/license scanned, and accompanied by an SBOM when distributable software is released. **AC:** mutable/unverified dependency or missing required SBOM blocks release; exceptions are approved and expiring. **Source:** V-GUARD/V-EVOL. **Verification:** SCA, provenance, and release tests. **Trace:** BG-05/BG-06; `TC-SR-002`.

**GH-SR-003 — Dependency management (Must).** Dependencies shall be inventoried, automatically monitored, reviewed before update, and remediated within organization severity timelines. **AC:** simulated critical advisory creates owned work and blocks affected release until resolved/accepted. **Source:** V-GUARD. **Verification:** dependency-control exercise. **Trace:** BG-05; `TC-SR-003`.

**GH-SR-004 — Code and secret scanning (Must).** Changes and default branches shall receive appropriate static/code, dependency, and secret scanning with protected alert triage. **AC:** seeded test findings are detected, access-controlled, assigned, and cannot be dismissed without rationale. **Source:** V-GUARD. **Verification:** scanner canary and process audit. **Trace:** BG-05; `TC-SR-004`.

**GH-SR-005 — Approvals and signing (Must).** Security-sensitive policy, registry enablement, workflow-permission, and release changes shall require designated human approval; commits and releases shall be cryptographically verified where organization tooling supports reliable enforcement, with documented exception handling. **AC:** missing approval/signature blocks governed action and verified identity is retained. **Source:** V-FLOW/V-GUARD. **Verification:** negative approval/signature tests. **Trace:** BG-02/BG-05; `TC-SR-005`.

**GH-SR-006 — Data protection (Must).** Inputs, logs, artifacts, prompts, and results shall be classified, minimized, sanitized, access-controlled, retained, and deleted according to policy; secrets and prohibited personal/confidential data shall not enter task contracts or AI prompts. **AC:** test secrets/sensitive patterns are blocked or redacted and retention settings match classification. **Source:** V-GUARD. **Verification:** DLP/log/retention audit. **Trace:** BG-05; `TC-SR-006`.

## 6. Quality requirements and lifecycle gates

**GH-QR-001 — Testing expectations (Must).** Changes shall provide risk-proportionate positive, negative, boundary, compatibility, security, concurrency, recovery, and regression evidence mapped to affected requirements. **AC:** impact analysis identifies tests; mandatory categories pass or have approved rationale. **Source:** V-RESP/V-EVOL. **Verification:** test-plan review and execution. **Trace:** BG-03/BG-05; `TC-QR-001`.

**GH-QR-002 — Linting and validation (Must).** All machine-readable contracts, configuration, workflows, code, links, and examples shall pass deterministic syntax, semantic, style, and consistency validation. **AC:** seeded syntax, schema, link, version, and policy defects are rejected. **Source:** V-PRIN. **Verification:** validation canaries. **Trace:** BG-03/BG-07; `TC-QR-002`.

**GH-QR-003 — Review quality (Must).** Pull requests shall state intent, requirement/interface impact, risk, evidence, security implications, compatibility, deployment/adoption, and rollback; reviewers shall be independent of the author for governed changes. **AC:** incomplete PR cannot satisfy review gate. **Source:** V-FLOW/V-EVOL. **Verification:** template and sampled review audit. **Trace:** BG-02/BG-06; `TC-QR-003`.

**GH-QR-004 — Definition of Ready (Must).** Work is ready only with approved vision/requirement trace, owner, bounded scope/non-scope, acceptance criteria, interfaces/dependencies, assumptions, risk/security/data classification, verification approach, and required reviewers. **AC:** missing mandatory field prevents ready state. **Source:** V-PRIN. **Verification:** issue workflow negative test. **Trace:** BG-01/BG-07; `TC-QR-004`.

**GH-QR-005 — Definition of Done (Must).** Work is done only when acceptance criteria and mapped tests pass; documentation/contracts/examples/traceability are current; security and compatibility findings are resolved; approvals are recorded; rollback/operations are ready; and no unauthorized merge/deployment occurred. **AC:** evidence checklist is complete and independently reviewable. **Source:** V-FLOW/V-EVOL. **Verification:** release/closure audit. **Trace:** BG-02/BG-06; `TC-QR-005`.

**GH-QR-006 — Documentation quality (Must).** Normative documents shall be complete, consistent, link-valid, reviewed by accountable stakeholders, and distinguish facts, requirements, assumptions, current state, and future state. **AC:** quality review finds no orphan requirement or unresolved normative contradiction. **Source:** V-PRIN. **Verification:** traceability/doc audit. **Trace:** BG-03/BG-07; `TC-QR-006`.

**GH-QR-007 — Workflow quality (Must).** Production workflows shall be deterministic for identical authoritative inputs, concurrency-safe, timeout-bounded, idempotency-aware, testable without production side effects, and explicit about failure. **AC:** replay, concurrency, timeout, and verify-mode tests pass and false-success test fails safely. **Source:** V-RESP/V-GUARD. **Verification:** workflow harness. **Trace:** BG-04/BG-05; `TC-QR-007`.

**GH-QR-008 — Continuous cross-repository interface simulation (Must).** The organization shall provide automated CI that validates the complete approved-issue-to-draft-PR interface across all four registered target profiles without calling Codex or creating a real branch or pull request. **AC:** authoritative deterministic fixtures cover valid request/result; unsupported version; malformed request; unauthorized, stale, or withdrawn approval; unknown/disabled target; duplicate delivery/result; existing managed draft PR; target rejection; execution/validation failure; and delayed, missing, or ambiguous result. Producer, router, receiver, source consumer, and target adapters must fail CI on incompatibility. A separately human-gated test may intentionally exercise real Codex-to-draft-PR behavior but is not normal CI. **Source:** V-EVOL/V-RESP; next-MVP objective. **Verification:** `TC-MVP-CI-001`, fixture canaries, and controlled `TC-MVP-E2E-001`. **Trace:** BG-01/BG-03/BG-04/BG-06; ADR-004/005/010; ARC-MVP-CONFORMANCE.
