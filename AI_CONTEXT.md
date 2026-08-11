# AI Context

## Purpose and usage

This file is the ordered entry point and standing implementation policy for AI
agents working in `Young-Consultations/.github`. Read it completely before
proposing or making any change, then follow the applicable sources in the
ordered reading path. It indexes canonical sources and supplies interpretation
rules; it does not duplicate or replace their requirements, decisions, or
interfaces.

Use only evidence available in this repository. References to other
repositories describe documented dependencies and ownership, not their current
files, behavior, approval, or conformance.

## Authority hierarchy

Interpret repository evidence in this order:

1. The approved [vision](docs/VISION.md) defines product direction, purpose,
   intended outcomes, scope, and boundaries.
2. The approved [requirements baseline](docs/requirements/README.md) defines
   behavior, constraints, interfaces, and acceptance conditions.
3. The [next-MVP planning baseline](docs/releases/next-mvp.md) selects and
   allocates the currently planned realization increment, acceptance scenario,
   exclusions, and deferrals within the approved requirements. It does not
   override or relax a normative requirement.
4. Approved [architecture and design](docs/architecture/README.md), including
   accepted [ADRs](docs/architecture/ADR.md), defines system structure,
   responsibility allocation, security boundaries, and architectural decisions.
5. Current organization and repository interface documentation defines
   cross-repository interactions and ownership boundaries.
6. Code, workflows, schemas, tests, fixtures, packages, examples, release
   artifacts, and other implementation artifacts are authoritative evidence
   of current behavior and must be treated as such; they do not override
   higher-authority intent, requirements, or design decisions.

An existing or operating implementation artifact does not override a higher
authority. After an artifact is deliberately aligned, it may enforce the
authoritative documentation executably; any later conflict must be reported
and resolved rather than silently redefining the requirement.

Preserve a document's stated approval status. Draft, proposed, planning,
superseded, or unapproved material is not promoted by being linked here. When
authoritative sources conflict or leave ownership materially undecided, do not
infer a resolution from implementation. Record the affected sources and IDs in
the **Known gaps or conflicts** section and report the issue to the appropriate
owners.

## Repository role and ownership

This repository is the organization AI-SDLC control plane. It owns the shared
canonical task, execution-input, and execution-result semantics; schemas and
validation; repository registration and routing policy; admission and result
boundaries; shared failure, identity, correlation, compatibility, verification,
and release policy; and the related architecture and boundary documentation.
For the next MVP it may also be a target for explicitly selected documentation,
CI, repository-maintenance, and testing work, but only through the separate,
target-only trust boundary established by ADR-011.

It does **not** own portfolio intake, priority, readiness, or approval; target
implementation logic, prompts, source modification, local testing, branch or
pull-request publication; consulting or software-factory internals; human
review and merge; deployment or production authorization; GitHub internals; or
AI-provider internals. It is not an operational secrets store.

The documented external dependencies are GitHub repositories, Actions, API,
Issues, Releases, organization identity and settings, registered task producers
and targets, and target-owned approved AI or third-party services. The
`portfolio-tasks` planning authority owns source tasks and approval provenance;
registered targets own local execution and draft publication; humans retain
merge and production authority. Sibling repository implementation and
conformance must be confirmed by their owners and are not assumed here.

## Ordered reading path

Read these sources in order, stopping to consult the identified detail when it
applies:

1. [Vision](docs/VISION.md) — product intent, repository responsibilities,
   non-responsibilities, principles, guardrails, and evolutionary direction.
2. [Requirements index](docs/requirements/README.md) — approval status,
   normative conventions, governance, and the complete requirements map. Then
   consult:
   - [project requirements](docs/requirements/project-requirements.md) for
     outcomes, scope, stakeholders, constraints, and future expansion;
   - [software requirements](docs/requirements/software-requirements.md) for
     normative functional, quality, operational, and security requirements;
   - [requirements traceability](docs/requirements/requirements-traceability.md)
     before changing behavior or acceptance evidence;
   - [repository context](docs/requirements/repository-context.md),
     [repository interfaces](docs/requirements/repository-interfaces.md), and
     [external interfaces](docs/requirements/external-interfaces.md) for
     ownership and integration boundaries.
3. [Next-MVP planning baseline](docs/releases/next-mvp.md) — the objective,
   responsibility allocation, acceptance scenario, exclusions, and deferrals
   that select and allocate work compliant with the requirements above.
4. [Architecture index](docs/architecture/README.md) — approved next-MVP design
   map and interpretation rules. Always consult [ADRs](docs/architecture/ADR.md)
   and [repository boundaries](docs/architecture/RepositoryBoundaries.md);
   consult [interface architecture](docs/architecture/InterfaceArchitecture.md),
   [integration architecture](docs/architecture/IntegrationArchitecture.md),
   and [security architecture](docs/architecture/SecurityArchitecture.md) for
   boundary changes; follow the index to the other component, flow, state,
   deployment, observability, error, configuration, extension, and traceability
   designs relevant to the task.
5. [MVP v2 interface baseline](docs/interfaces/mvp-v2-compatibility.md) — the
   single current organization payload family, workflow obligations,
   conformance matrix, trust separation, and deployment gates. Also consult the
   normative interface requirements linked above.
6. [Repository README](README.md) — repository navigation and locally described
   package and verification usage; [contract overview](contracts/README.md),
   [router documentation](docs/codex-router.md), and [release policy](docs/releases.md)
   provide implementation and operational context only after the authorities
   above have established the required behavior.

There is no locally present `AGENTS.md`, `CONTRIBUTING.md`, standalone coding
standard, or standalone prompt-rules document at the time of this review. If
one is later added, obey its scoped instructions without allowing it to
silently override approved higher-authority product documentation.

## Implementation authority and compatibility policy

- The approved vision and requirements, followed by applicable approved
  architecture/design and accepted ADRs, are implementation authority. The
  next-MVP planning baseline selects and allocates compliant work but cannot
  override their normative obligations. Before **every**
  implementation task, load this file first and follow its ordered reading path
  and repository boundaries before inspecting implementation details or editing.
- Per the approved requirements baseline and current release documentation,
  the project is pre-production and no backward-compatibility requirement has
  been approved. These facts do not weaken governance or security controls.
- Existing implementation is a blueprint, not the product authority. Reuse an
  artifact only when it conforms to approved requirements and design.
- A later authorized implementation task may modify, replace, or remove
  conflicting, duplicated, obsolete, or out-of-scope code, workflows, schemas,
  tests, fixtures, packages, and examples. Git history is the recovery
  mechanism for removed historical behavior.
- The organization supports exactly **one active cross-repository contract**
  and **one current execution path**. For this MVP, the locally authoritative
  interface baseline identifies that contract as the closed v2 task,
  `execution-input/v2`, and `execution-result/v2` family. This statement is a
  policy and required target state, not a claim that every current artifact or
  consumer is already aligned.
- Do not preserve backward compatibility, deprecated execution paths, duplicate
  contracts, wrappers, aliases, transitional structures, earlier contract
  shapes, compatibility adapters, migration layers, dual-schema validation,
  obsolete workflow inputs, or fallback interfaces unless an authoritative
  requirement explicitly requires them. A version field or discriminator may
  identify the single current payload shape; it does not require support for
  earlier versions.
- Repository-local interfaces must conform to that single organization
  contract as defined by the locally available authoritative interface
  documentation. Historical releases may remain immutable evidence without
  being active interfaces.
- This documentation-only task does not authorize deletion, replacement,
  contract modification, workflow modification, or other implementation work.
- Do not invent missing requirements, architecture, external behavior, or
  integration details. When work depends on an undecided external interface or
  unavailable owner decision, fail closed and report the blocker; use only
  explicit, versioned interface or release documents in this repository for
  cross-repository assumptions.

## MVP boundaries

The included `.github` responsibilities are approved v2 task admission;
canonical input and result rules; four-target registration with gated
enablement; deterministic routing; explicit read-only `verify` and draft-only
`implement` modes; a reusable result-receiver boundary; delivery correlation
and idempotent visible effects; shared deterministic no-Codex conformance;
release governance; and a separately authorized `.github` target adapter. The
end-to-end MVP ends at one validated draft pull request and one correlated
canonical result. Planned capabilities must not be described as implemented
without implementation evidence.

Explicitly excluded are exactly-once transport, autonomous approval, automatic
merge, release or deployment automation authority, production operation,
production-scale SLO claims, and unrelated product, portfolio, consulting, or
target-specific behavior. Rich v3 approval provenance, additional modes,
additional lifecycle contracts, additional targets, provider-neutral profiles,
attestations, metrics, and retention exports are deferred pending separate
approval. `GH-FR-016` and other production-maturity work not needed for the MVP
are deferred by the next-MVP allocation.

## Security and change boundaries

- Human approval must precede executable work. Automation may publish only a
  draft proposal; it must never approve, clear draft state, merge, deploy,
  authorize production, mutate organization settings, or push directly to a
  protected default branch.
- Fail closed on missing, stale, malformed, incompatible, ambiguous, or
  unauthorized identity, approval, version, registry, target, mode, or result
  evidence. GitHub Projects and discussions cannot authorize execution.
- Enforce exact repository and workflow allowlists, closed schemas, immutable
  production pins, target-side revalidation, target isolation, and idempotent
  delivery effects. The control-plane and `.github` target identities and
  credentials remain separate.
- Use least-privilege, preferably short-lived credentials. Never pass
  control-plane credentials to targets or AI providers, and never put secrets,
  tokens, private URLs, authorization headers, or disallowed confidential or
  personal data in contracts, prompts, source, logs, artifacts, diagnostics, or
  this file. Minimize and sanitize data and evidence.
- Do not modify a repository outside the explicitly declared target. Preserve
  repository-local execution ownership and human-controlled cleanup, release,
  deployment, and production operations.
- Security, registry, release, permission, retention, reconciliation, target
  enablement, and immutable-pin decisions retain their documented human review
  and approval gates.

## Development and validation workflow

Keep every change focused on its approved scope, cite applicable requirement
and architecture IDs, and run the tests that cover the affected behavior. The
checked-in CI configuration supports these local commands after installing the
packages declared in [`requirements-dev.txt`](requirements-dev.txt):

```console
python -m pytest
python scripts/validate_release.py
python scripts/verify_target_workflows.py
git diff --check
```

`python scripts/verify_target_workflows.py` is applicable only when its
documented target-workflow credentials and external access are available; pass
`--fixtures-only` to run the script in offline mode without live credentials.
The target compatibility workflow separately runs its local pytest coverage.
Documentation-only work must at minimum validate Markdown links, review the
diff and changed-file list, apply any available Markdown checks, scan for
sensitive or unsupported claims, and run `git diff --check`. No standalone
Markdown linter is configured in this repository.

## Rules for future AI implementation tasks

Every later agent must:

1. Read this file completely and identify the applicable approved vision,
   requirement IDs, architecture/design sources, ADRs, interfaces, security
   controls, and acceptance evidence before editing.
2. Treat all existing implementation artifacts as blueprints. Retain them only
   when evidence shows alignment; do not infer scope or authority from their
   existence.
3. Keep the change focused, preserve required behavior, and run the full
   applicable validation suite.
4. Never silently change approved requirements, architecture, ownership,
   security boundaries, or the single active contract/current path. Report a
   material contradiction with source names and IDs rather than resolving it
   from code or introducing a compatibility path.

Before removing or replacing an artifact in a later authorized task, the agent
must:

1. Identify the active, obsolete, duplicated, or deferred behavior it supports.
2. Trace that behavior to applicable requirements, architecture, interface
   documentation, or ADRs.
3. Search for and address every reference and dependency.
4. Preserve behavior required by an active requirement.
5. Update affected tests and documentation consistently.
6. Verify that no orphaned imports, links, workflow references, schema
   references, fixtures, or package dependencies remain.
7. Run the full applicable validation suite.
8. Report every material removal or replacement and its reason.

Legacy-looking artifacts are not automatically deleted; each disposition is
decided and justified during the relevant implementation task.

## Known gaps or conflicts

- The organization-owned [MVP v2 interface baseline](docs/interfaces/mvp-v2-compatibility.md)
  records that the declared `ai-sdlc-v2.2.0` tag does not exist and that its
  complete fixture manifest is identified only at a recorded commit. The
  next-MVP baseline also states that executable inputs, expected outputs, and
  deterministic fake adapters are not complete for every `TC-MVP-CI-001`
  scenario. These are implementation and release-evidence gaps, not permission
  to create another active contract.
- `CC-MVP-SOURCE` and `CC-MVP-TARGET` conformance, sibling-repository-specific
  requirement IDs, immutable adapter revisions, target enablement, credentials,
  retention duration, and reconciliation deadline remain pending their
  documented owner confirmation or human governance decisions. This repository
  does not establish their current state.
- ADR-001, ADR-002, ADR-005, ADR-006, and ADR-007 retain explicitly documented
  open questions. They block invention in the affected area but do not relax
  their decisions or authorize implementation artifacts to answer them.
- The previous context policy treated current versioned contracts, workflows,
  tests, registry, and release documentation as authoritative for implemented
  behavior and directed agents to preserve schema compatibility. That rule has
  been replaced by the authority hierarchy and single-active-contract policy
  above: implementation is evidence, and backward compatibility is not
  currently required.
- The approved [architecture index](docs/architecture/README.md) identifies the
  next-MVP architecture as approved and normative, while
  [Software Architecture](docs/architecture/SoftwareArchitecture.md) and
  [Architecture Traceability](docs/architecture/ArchitectureTraceability.md)
  expressly retain pre-approval language. This status conflict requires owner
  reconciliation. When implementation depends on either named document, fail
  closed and report the conflicting status; do not treat its content as
  approved or dismiss its stated status as stale.

No other material contradiction among the locally approved vision,
requirements, applicable approved architecture, and v2 interface direction was
identified during this task. The gaps above must remain visible and fail closed
where applicable.

## Maintenance rule

Update this file in the same focused change whenever an authoritative file
moves, its approval status changes, ownership boundaries change, or the current
interface policy changes. Recheck every relative link and command whenever it
is edited. Keep historical behavior in Git history, release records, or ADRs;
do not maintain multiple active policies or compatibility paths in this index.
