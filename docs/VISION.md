# Young Consultations AI-SDLC Vision

This document is authoritative for organization and control-plane intent. It
defines the destination and boundaries from which requirements are to be
developed. It does not assert that every described capability is implemented;
the versioned contracts, registry, workflows, tests, and release documentation
remain authoritative for current behavior.

## Organization Vision

Young Consultations is building a governed AI-assisted software development operating system that turns human intent into approved, traceable, and reviewable software delivery. GitHub serves as the system of record for portfolio decisions, engineering work, execution evidence, and human approval. Specialized repositories collaborate through explicit versioned contracts so that planning, governance, AI execution, product generation, and consulting knowledge can evolve independently without sacrificing safety, accountability, or architectural coherence.

## Organization Purpose

The organization exists to enable a software leader, consultant, or small
engineering team to move from an idea or business need through the professional
software development lifecycle with substantially greater leverage from AI,
while retaining human authority over priorities, sensitive decisions, and
production changes.

The long-term direction is a modular ecosystem able to support product vision,
requirements development, planning and decomposition, architecture and design,
implementation, testing and verification, security review, documentation,
release and deployment, operational learning, and consulting assessment and
delivery guidance. Expansion is controlled capability growth through explicit
contracts, not an unrestricted autonomous agent.

## Desired End-to-End Experience

The organization seeks a repeatable path:

> Human intent
> → structured portfolio task
> → explicit approval
> → authorized repository routing
> → bounded AI execution
> → validation and engineering evidence
> → draft pull request
> → human review and merge
> → traceable delivery outcome

AI may prepare, analyze, generate, validate, and propose changes. Humans remain
responsible for approving executable work, reviewing consequential decisions,
merging code, and authorizing production use.

## Guiding Principles

- **GitHub is the system of record.** Portfolio decisions, engineering work,
  execution evidence, and approvals have durable GitHub identities.
- **Human approval precedes executable work.** An AI executor does not turn an
  unapproved proposal into repository changes.
- **AI execution is bounded and auditable.** Authorization, scope, identity,
  evidence, and outcomes are inspectable.
- **Contracts are explicit and versioned.** Participants exchange defined
  interfaces rather than relying on incidental implementation details.
- **Repositories have single, documented responsibility boundaries.** No
  repository silently absorbs another repository's responsibilities.
- **Verification must fail closed.** Missing, invalid, incompatible, or
  unauthorized information prevents execution rather than weakening policy.
- **Generated changes are published through draft pull requests.** Automation
  proposes reviewable changes rather than treating generation as acceptance.
- **Automatic merge is outside the supported model.** Merge authority remains
  human.
- **Cross-repository behavior must not depend on undocumented knowledge.**
  Shared behavior is expressed through contracts, registration, policy, and
  documented interfaces.
- **Requirements must trace back to an approved vision capability or
  constraint.** The next lifecycle phase refines this vision rather than
  inventing an unrelated scope.

## Repository Operating Model

The organization uses four repositories with distinct responsibilities. These
descriptions establish boundaries, not claims about the repositories' current
implementation:

- `Young-Consultations/.github` owns organization-wide AI-SDLC contracts,
  routing policy, repository registration, compatibility boundaries, and
  shared verification.
- `Young-Consultations/portfolio-tasks` owns portfolio intake, backlog
  governance, prioritization metadata, approval state, and initiation of
  approved work.
- `Young-Consultations/slugger` owns the AI Software Factory product and the
  controlled generation and validation of software projects.
- `Young-Consultations/consulting-playbook` owns reusable consulting methods,
  assessments, decision frameworks, delivery playbooks, and consulting
  knowledge that can produce governed portfolio work.

No repository should silently absorb another repository's responsibilities.
Planning and execution repositories collaborate with the control plane only
through documented, versioned boundaries.

## Vision for Young-Consultations/.github

Young-Consultations/.github is the organization’s AI-SDLC control plane. It provides the stable, versioned, and testable contracts through which approved work is authorized and routed to registered repositories. It enables independent repository execution while enforcing organization-wide safety, compatibility, traceability, and ownership boundaries.

This repository exists to make cross-repository AI-assisted delivery
predictable and governable. It defines the shared language and routing boundary
used by planning repositories and execution repositories, but it does not plan
portfolio work or modify target-repository source code.

The vision is informed by the current control-plane shape: canonical task,
execution-input, and execution-result schemas; a shared validator; a repository
registry; a reusable router; read-only contract verification; a router smoke
test; and an immutable release lifecycle. Those artifacts describe the current
implementation. This document describes why that architecture exists and the
direction in which it may evolve.

## Repository Responsibilities

The control plane owns:

- canonical task, execution-input, and execution-result contracts;
- shared contract schemas and validation libraries;
- organization-level repository registration and routing policy;
- organization router behavior;
- contract versioning, compatibility, release, deprecation, and rollback
  policy;
- shared failure classifications and correlation behavior;
- control-plane contract tests and routing verification; and
- documentation of platform-level ownership boundaries.

Its success state is one approved canonical task routed exactly once to the
correct registered repository, interpreted consistently by the target, and
reported through one canonical result, with explicit, diagnosable, and safe
failures. This is a vision-level outcome, not a claim of transactional
exactly-once execution. The current architecture documents at-least-once
delivery with target-side idempotency to produce exactly-once externally
visible publication effects for a canonical delivery identity.

## Explicit Non-Responsibilities

The control plane does not own:

- portfolio prioritization;
- task approval decisions;
- product requirements;
- consulting methodology;
- target-repository implementation logic;
- direct Codex modification of registered target repositories;
- automatic merging; or
- production deployment authorization.

Target repositories retain repository-specific execution, validation, branch,
and draft-pull-request behavior. This repository validates and routes; it does
not become a shared implementation engine.

## Users and Stakeholders

- **Organization owner:** establishes organization intent, governance limits,
  and final accountability.
- **Software engineering lead:** maintains architectural coherence and turns
  approved vision into coordinated engineering direction.
- **Portfolio manager:** governs intake, prioritization, approval state, and
  portfolio visibility outside this repository.
- **Repository maintainer:** adopts compatible control-plane releases and owns
  repository policy and health.
- **Target-repository developer:** implements and reviews repository-specific
  behavior behind the shared integration boundary.
- **Codex or another bounded AI executor:** consumes authorized inputs and
  prepares auditable outcomes within declared limits.
- **Contract and release maintainer:** evolves schemas, validators,
  compatibility evidence, releases, deprecations, and rollback guidance.
- **Auditor or reviewer:** examines authorization, provenance, evidence,
  failures, and proposed changes before consequential decisions.

These stakeholder descriptions express roles in the operating model; they do
not imply market research, interviews, or user-volume findings.

## Measures of Vision Success

Vision success is visible through qualitative outcomes:

- ownership between the control plane and target repositories is unambiguous;
- participants achieve versioned interoperability without sharing hidden
  implementation knowledge;
- routing is deterministic, authorized, and limited to registered targets;
- execution identity is traceable from approved intent through result and
  review evidence;
- invalid, unauthorized, incompatible, and uncertain states fail safely and
  diagnostically;
- target repositories can evolve independently while deliberately adopting
  compatible control-plane releases;
- human reviewers receive clear validation and engineering evidence with each
  proposed change; and
- the vision provides a reliable, bounded foundation for requirements
  development.

## Constraints and Guardrails

- GitHub remains the system of record and executable work originates from an
  approved, canonical task rather than an informal side channel.
- Human approval is required before execution, humans retain merge authority,
  and production use requires human authorization.
- The router authorizes and routes but does not modify target source code.
- Targets are explicitly registered and integrations use canonical, versioned
  contracts with controlled credentials and least privilege.
- Contract, authorization, dependency, routing, compatibility, and
  verification uncertainty fails closed with sanitized, diagnosable results.
- Automated publication is limited to deterministic branches and draft pull
  requests; direct default-branch changes and automatic merges are excluded.
- Shared policy does not acquire repository-specific parsing or execution
  logic merely for convenience.
- Planned capability is not current behavior until it appears in the applicable
  released contracts, policy, workflows, and verification evidence.

## Evolution Strategy

The control plane evolves through versioned contracts, compatibility tests,
immutable releases, deliberate target adoption, and documented rollback paths.
Deprecation is explicit, and a target can remain on or return to a known
compatible immutable release while change is assessed. Repository-specific
behavior remains outside the control plane unless it is genuinely an
organization-wide contract concern.

Capability growth follows the professional lifecycle areas described in the
organization purpose, but each expansion must preserve human governance,
least-privilege routing, traceability, independent repository ownership, and
fail-closed verification. The current contracts and workflows are the baseline
for assessing change; the broader lifecycle direction is not evidence that a
capability is already delivered.

## Transition to Requirements Development

The current organization-level realization increment is defined in the
[next-MVP baseline](releases/next-mvp.md). That baseline traces this vision into
measurable requirements and tests; it does not change the vision or turn this
document into a workflow specification.

The next phase is to derive and approve requirements, not to add implementation
detail to this vision. The proposed traceability hierarchy is:

> Organization vision
> → organization capabilities
> → organization constraints
> → repository vision
> → repository capabilities
> → functional requirements
> → non-functional requirements
> → interface and contract requirements
> → verification criteria
> → backlog epics and issues

Requirements development must address these capability areas without assuming
that the vision itself supplies requirements or acceptance criteria:

| Capability area | Scope for the requirements phase |
| --- | --- |
| Canonical contract management | Define the governed lifecycle and ownership of the task, execution-input, and execution-result language shared by participants. |
| Repository registration | Define how target identity, eligibility, routing metadata, and enablement state are governed. |
| Authorized routing | Define the boundary that admits approved work and selects only a permitted registered target and workflow. |
| Identity and correlation | Define durable identities that connect source intent, delivery attempts, execution evidence, and reported outcomes. |
| Exactly-once routing behavior | Define the intended observable uniqueness outcome and its relationship to retries, at-least-once delivery, and target idempotency. |
| Execution-mode semantics | Define the shared meaning and limits of verification and implementation modes without taking over target execution. |
| Compatibility and version lifecycle | Define compatibility assessment, immutable version adoption, deprecation, migration, and support boundaries. |
| Failure classification | Define common failure meaning and safe diagnostic propagation across planning, routing, and execution boundaries. |
| Security and least privilege | Define authorization, credential scope, trust boundaries, data handling, and prohibited actions. |
| Verification and test evidence | Define the evidence needed to demonstrate contract, router, target-integration, and end-to-end confidence. |
| Observability and auditability | Define the records and associations needed for people to reconstruct decisions, attempts, failures, and outcomes. |
| Target-repository integration | Define the interface obligations that allow targets to execute independently while interoperating with the control plane. |
| Rollback and recovery | Define safe restoration, target isolation, redelivery, and recovery concepts across version and execution failures. |

Each resulting requirement should trace upward to an approved capability or
constraint and downward to verification criteria and governed backlog work.
Detailed requirements, shall-statements, acceptance criteria, and user stories
belong to that next phase and are intentionally absent here.

## Vision Assumptions Requiring Validation

These assumptions preserve the intended boundary while requirements are being
developed; validation may confirm them or identify a need for an explicitly
approved vision change.

| Assumption | Why it matters | Requirements-phase validation method |
| --- | --- | --- |
| GitHub Issues remain the authoritative source of executable work. | A single initiation source prevents ambiguous or unauthorized execution. | Map proposed initiation and approval flows to durable issue identity and review governance. |
| GitHub Projects remain a reporting and planning surface rather than an execution source. | Separating visualization from initiation avoids competing sources of truth. | Examine portfolio-state use cases and confirm that project changes cannot independently authorize execution. |
| Target repositories retain their own execution workflows. | Local execution ownership preserves repository boundaries and independent evolution. | Allocate workflow responsibilities and validate each shared interface against representative target integration scenarios. |
| Draft pull requests remain the only automated publication mechanism. | Draft publication keeps generated changes reviewable and non-final. | Trace every automated change-publication scenario and identify any path that bypasses a draft pull request. |
| Humans retain merge authority. | Human accountability depends on automation being unable to accept its own proposed changes. | Model permissions and decision roles, then review merge-related threat and governance scenarios. |
| Contract releases are consumed through explicit immutable version pins. | Reproducibility, deliberate adoption, and rollback depend on stable consumed versions. | Define consumer upgrade and rollback scenarios and verify that all supported references resolve to immutable releases. |
