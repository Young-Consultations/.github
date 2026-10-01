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
validation; immutable target capabilities, mutable activation, and routing
policy; admission and result boundaries; shared failure, identity, correlation,
compatibility, verification, and release policy; and the related architecture
and boundary documentation. For the next MVP it may also be a target for
explicitly selected documentation, CI, repository-maintenance, and testing work,
but only through the separate target-only trust boundary established by
ADR-011.

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
   that select and allocate work compliant with the requirements above. For
   work on the controlled end-to-end acceptance path, also read the approved
   [TC-MVP-E2E-001 acceptance design](docs/acceptance/TC-MVP-E2E-001.md), which
   defines the shared SIM/REAL architecture, corrective compatibility boundary,
   and human-trigger rule.
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
   conformance matrix, trust separation, retry semantics, and deployment gates.
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
  override their normative obligations. Before **every** implementation task,
  load this file first and follow its ordered reading path and repository
  boundaries before inspecting implementation details or editing.
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
  `execution-input/v2`, and `execution-result/v2` family. Release SemVer may
  advance independently of that payload namespace.
- Do not preserve deprecated execution paths, duplicate contracts, wrappers,
  aliases, transitional structures, earlier contract shapes, compatibility
  adapters, migration layers, dual-schema validation, obsolete workflow inputs,
  or fallback interfaces unless an authoritative requirement explicitly
  requires them.
- Repository-local interfaces must conform to the single organization contract
  as defined by the locally available authoritative interface documentation.
  Historical releases remain immutable evidence and are not silently
  reinterpreted when a corrective release is prepared.
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

`TC-MVP-E2E-001` is one acceptance architecture with two modes, not two
execution paths. `TC-MVP-E2E-001-SIM` resolves and executes the exact immutable
adapter of the sole enabled target through deterministic fake Codex/publication
effects and passes target-produced results through the current control-plane receiver logic using in-memory journal/forwarding effects. Published 3.0.3 binds the enabled consulting target to immutable `codex-adapter-v3.0.3`, whose target workflow pins the 3.0.3 credential preflight and receiver. The receiver accepts the reviewed 3.0.1, 3.0.2, and 3.0.3 admission releases, and target compatibility constrains cross-release admission reuse to that pinned receiver policy. Portfolio-tasks consumes 3.0.3 through merged PR #163 after deployed Runtime Preflight 36867504568 and immutable REAL readiness preflight 36867939797 passed. `TC-MVP-E2E-001-REAL` uses the
existing source, router, target, receiver, and source-projection path after a
non-mutating preflight. The REAL execution trigger remains the existing
authorized-human `status:approved` action in `portfolio-tasks`; the control
plane must not fabricate source approval, impersonate a target, or introduce a
second execution engine. Passing SIM is required before REAL and never counts
as REAL acceptance.

Historical compatibility evidence remains immutable. The 2.3.2 compatibility
unit at commit `5738ace3ee90dde11336f8f8099e64e5645f7139` and the 2.4.0 receiver
retry correction explain earlier contract evolution, but they are not the
current control-plane release. The current published control-plane compatibility
release is `ai-sdlc-v3.0.3` at reviewed PR #104 merge commit
`f3229bfa4a06da963cae7c390c6075b4f6c12f7b`. It preserves
`ai-sdlc-contract/v2`, the resolved idempotent
`draft-pr-created -> duplicate-reused` receiver semantics, and the dedicated
GitHub App result-writer credential interface introduced by 3.0.0. The 3.0.3
PATCH repairs cross-release admission reuse while preserving the 3.0.2
receiver-compatibility repair and 3.0.1 organization-secret metadata repair as
immutable predecessor evidence.

Historical 2.4.3 replacement evidence remains quarantined as incident history.
Do not infer current readiness, rollback safety, or activation from older tags.
Publication and live consumption are separate evidence gates. Published
`ai-sdlc-v3.0.3` is the current control-plane compatibility release at
reviewed PR #104 merge commit `f3229bfa4a06da963cae7c390c6075b4f6c12f7b`; portfolio-tasks consumes
published 3.0.3 through PR #163. Deployed Runtime Preflight 36867504568 and
immutable REAL readiness preflight 36867939797 passed before that source
cutover. Fresh #159 then preserved its original trusted 3.0.1 admission and
stable delivery identity, produced one managed draft PR #82 and one terminal
source projection, and on unchanged redelivery returned `duplicate-reused`
before Codex with no second receiver/source visible effect. DEF-0073,
DEF-0064, and DEF-0086 are resolved. Unrelated terminal delivery identities
remain non-reusable.

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
python scripts/verify_release_target_workflows.py --repository OWNER/REPOSITORY
python scripts/verify_release_target_workflows.py --enabled-only
git diff --check
```

`python scripts/validate_release.py` verifies structural release coherence.
Published control-plane compatibility state is `ai-sdlc-v3.0.3` at reviewed
PR #104 merge commit `f3229bfa4a06da963cae7c390c6075b4f6c12f7b`. The manifest records
`tag_published: true` with that exact `tag_commit_sha`. Portfolio-tasks now
consumes 3.0.3 through PR #163 at `580eaf3cd88774014d645d3c3ca3718b39b38ce0`.
Deployed Runtime Preflight 36867504568, immutable REAL readiness preflight
36867939797, first REAL target/receiver run 36911342397, source projection
36911478182, and unchanged redelivery target run 36913463403 all passed. The
second delivery returned `duplicate-reused` before Codex with no second
receiver/source visible effect.

During any future pre-publication candidate window,
`verify_release_target_workflows.py` delegates to normal remote verification
first and may use the current reviewed checkout only when a target pins the
exact manifest tag, the manifest explicitly records `tag_published: false` and
`tag_commit_sha: null`, and GitHub confirms that exact tag is absent. All other
missing, substituted, or incompatible refs remain fail-closed. For published
releases, remote immutable verification takes precedence. Historical 2.4.3 tag
replacement evidence must not be used as current release guidance.

Conformance reports identify a canonical non-recursive v2 pin of exact shared
and target files. They never predict the SHA of the commit that contains them;
the registry later binds the immutable adapter tag to its resolved commit and
the report digest as separate checks (ADR-015). Static workflow inspection
proves only the transport and receiver boundary. Idempotency and publication
behavior must be executed through the exact adapter and harness blobs bound by
that pin; comments or keyword presence are never behavioral evidence. Preflight
must observe both the deterministic branch and all pull-request state before
Codex, and inconsistent ownership fails `ambiguous-rejected` (ADR-016).

For `TC-MVP-E2E-001`, the repository workflow
`.github/workflows/tc-mvp-e2e-001.yml` runs the deterministic SIM path on pull
requests and supports manual SIM or REAL-preflight dispatch. REAL-preflight is
non-mutating and must remain blocked while the immutable corrective release tag
is absent or the selected target receiver pin is stale. A real Codex acceptance
execution is never started by that workflow. Only after the corrective release
tag exists, green REAL preflight, and source revision review does an authorized
human trigger the existing source-owned `portfolio-tasks` approval event
described in `docs/acceptance/TC-MVP-E2E-001.md`.

`python scripts/verify_target_workflows.py` is the normal immutable target
verifier. The release-aware wrapper is applicable only to release-gate
verification and only for the exact current manifest tag before it is created;
it must never be used as a general fallback for missing receiver refs. Both
commands require their documented target-workflow credentials and external
access for live checks; pass `--fixtures-only` to the normal verifier for
offline target-fixture validation. The target compatibility workflow separately
runs its local pytest coverage. Documentation-only work must at minimum validate
Markdown links, review the diff and changed-file list, apply any available
Markdown checks, scan for sensitive or unsupported claims, and run
`git diff --check`. No standalone Markdown linter is configured in this
repository.

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

For the 3.x cutover, Runtime Preflight must verify the source
projector's operational sender allowlist, not only the existence of its
repository variable. `portfolio-tasks` variable `PORTFOLIO_RESULT_SENDERS`
must exactly match the immutable `trusted_result_authors` set
(`ai-sdlc-result-writer[bot]` for this release) before cost-bearing REAL
execution. Because published 2.4.5 still uses the prior sender, perform this
variable cutover only after new 2.4.5 implementation dispatch is stopped and
before deployed corrective-release preflight/REAL acceptance. Organization issue #89 tracks
the pre-publication gap that led to this invariant.

## Known gaps or conflicts

- Live verification of the published 2.3.1 registry found that the
  `portfolio-tasks` and `slugger` conformance pins omitted the exact
  report-producing harness even though local tests and reports were green. The
  original tags remain immutable. Their 2.3.2 adapter tags bind the harness and
  preserve complete no-prohibited-effect evidence; the 2.3.2 control-plane
  registry records those tag/commit/report-digest tuples.
- Subsequent governance review approved `consulting-playbook` as the sole
  enabled target. Its corrected `codex-adapter-v2.4.3` now resolves to commit
  `050dc7bb4832eab77fca3e070d2ea1917d82e26e`; `.github`, `portfolio-tasks`, and
  `slugger` remain disabled.
- DEF-0032 was published in 2.4.0. The owner-authorized 2.4.3 identity rewrite
  conflicts with the normal immutable-tag rules in GH-FR-014, GH-OR-005,
  EI-07, IF-09, and `docs/releases.md`; that exception is explicit and limited
  to replacing the defective 2.4.3 target and control-plane identities. The
  prior 2.4.3 evidence is quarantined and cannot support REAL acceptance.
- Deployed Runtime Preflight run 36277959203 and immutable REAL preflight run
  36278028013 passed on the attested 2.4.5 control plane. The portfolio source
  consumer then advanced to 2.4.5, and fresh REAL issue #154 completed the live
  source -> router -> target -> managed draft -> receiver -> source projection
  path successfully.
- Repository-specific requirement IDs, credentials, retention duration, and
  reconciliation deadline remain pending their documented owner confirmation
  or human governance decisions. Further target enablement also requires an
  explicit governance decision; this repository records only the approved
  `consulting-playbook` activation. Required REAL acceptance credentials must
  be confirmed by their existing owners before the human-triggered live run;
  this repository must not invent a new cross-repository credential or bypass
  the source-owned approval gate to compensate for missing confirmation.
- ADR-001, ADR-002, ADR-005, ADR-006, and ADR-007 retain explicitly documented
  open questions. They block invention in the affected area but do not relax
  their decisions or authorize implementation artifacts to answer them.
- The previous context policy treated current versioned contracts, workflows,
  tests, registry, and release documentation as authoritative for implemented
  behavior and directed agents to preserve schema compatibility. That rule has
  been replaced by the authority hierarchy and single-active-contract policy
  above: implementation is evidence, and compatibility/release changes follow
  the current approved release policy rather than accidental historical code.

No unresolved architectural speculation is recorded here. The 2.4.5 release
path is the current verified control-plane state. Separate unresolved governance
work, including organization issue #77 for broader cost-bearing prerequisite
safety and any future target-enablement decisions, remains outside this release
record and must not be inferred from implementation artifacts.

## Maintenance rule

Update this file in the same focused change whenever an authoritative file
moves, its approval status changes, ownership boundaries change, or the current
interface policy changes. Recheck every relative link and command whenever it
is edited. Keep historical behavior in Git history, release records, or ADRs;
do not maintain multiple active policies or compatibility paths in this index.


## 3.0.3 published cross-release admission reuse repair

DEF-0086 was discovered after successful #159 reconciliation proved that the
source could preserve its original trusted 3.0.1 admission across the 3.0.2
cutover. The published 3.0.2 router would still reject that admission on
unchanged retry because it regenerated current release/activation evidence and
required exact binding equality.

Published 3.0.3 preserves the durable admission instead. Same-release
exact-binding reuse remains unconditional; cross-release reuse is allowed only
by target-bound immutable policy and must be accepted by the exact pinned
receiver compatibility policy. Admission journal creation is re-read after POST
so concurrent or ambiguous router-owned markers fail closed before dispatch.

The published manifest records `ai-sdlc-v3.0.3`,
`tag_published: true`, and
`tag_commit_sha: f3229bfa4a06da963cae7c390c6075b4f6c12f7b`. The matching immutable target is
`codex-adapter-v3.0.3` at
`f11852c7f563df16ea4afa9ab75bf766242e7327`.

Publication and source adoption remain separate evidence gates. For 3.0.3,
deployed Runtime Preflight 36867504568, immutable REAL readiness preflight
36867939797, and reviewed portfolio consumer PR #163 are complete. Fresh #159
also completed the required terminal plus unchanged same-delivery redelivery
acceptance sequence.

## 3.0.2 published receiver compatibility repair

REAL #159 exposed DEF-0073 after the result-writer credential prerequisites
passed: the 3.0.0 receiver rejected a valid 3.0.1 admission because it forced
the admission's control-plane release identity to equal the receiver bundle
release. The resolved architecture separates those identities and uses an
immutable receiver-owned compatibility allowlist instead of string equality.

The published control-plane release is `ai-sdlc-v3.0.2` at
`eae81af30eb8f1e2cf51a30b1e5a6d7dbd76bc6e`. The enabled consulting target
is immutable `codex-adapter-v3.0.2` at
`3bde0dc760088b9af21454a0f70ed498dae043a7`, with conformance adapter
revision
`sha256:1af153a276e2a3a87f6dd274a0aae111f09350a6a4995d874bd0014174e0ee04`
and report SHA-256
`f7251f7ac3ceb46c350106b9d3190f52be71ffd0b57a0faca5dffe2d847074e6`.
The compatibility policy accepts 3.0.1 admissions only as an explicitly
reviewed predecessor needed to recover the already-admitted #159 delivery, and
accepts 3.0.2 for new admissions after source adoption. Unsupported release
combinations remain fail-closed.

Portfolio-tasks now consumes 3.0.2 after the required deployed preflights.
Source reconciliation run 36666315992 then preserved #159's original trusted
3.0.1 admission and cleared the queued state without fabricating a terminal
result. That recovery exposed DEF-0086 at the router's cross-release admission
reuse boundary. Published 3.0.3 must pass deployed Runtime Preflight and
immutable REAL preflight and be source-adopted before #159 is reauthorized.
Controlled REAL terminal projection and unchanged same-delivery redelivery
remain required before closing the applicable acceptance defects.

## 3.0.1 published Runtime Preflight organization-secret repair

Deployed 3.0.0 Runtime Preflight run 36370005352 failed closed before Codex
because the auditor checked `AI_SDLC_RESULT_WRITER_PRIVATE_KEY` only through
repository-secret metadata even though the reviewed deployment stores it as an
organization Actions secret restricted to consulting-playbook. Organization
issue #93 tracks this false-negative prerequisite defect.

The resolved audit rule is storage-scope aware: repository/environment secrets
use their native metadata endpoints; an organization secret can satisfy a
repository role only when it belongs to the repository owner, uses
`selected` visibility, and explicitly selects the exact repository. Secret
values are never read. `PREFLIGHT_AUDIT_TOKEN` therefore needs organization
Actions Secrets read metadata access in addition to its prior repository-level
audit access.

The corrective control-plane release is `ai-sdlc-v3.0.1` at
`a98730deb729cc35dbd4d699395a87facb3ec78e`; it reuses immutable
`codex-adapter-v3.0.0` because no target code or interface changes. Published
`ai-sdlc-v3.0.0` remains immutable predecessor evidence. The failed deployed preflight
reported no `PORTFOLIO_RESULT_SENDERS` mismatch, so the live sender binding
has already been cut over to `ai-sdlc-result-writer[bot]`. Portfolio-tasks now consumes 3.0.1. That release is immutable predecessor
evidence; current release and cutover guidance is defined by the 3.0.2 section
above.

## 3.0.0 published result-writer identity release

REAL issue #156 proved target-side managed-draft reuse without a second Codex
execution but exposed control-plane defect #83: the deployed result credential
wrote receiver journal markers as `mightyjoe909` while the immutable result
trust policy expected `github-actions[bot]`. The receiver therefore could not
recognize its own prior durable evidence and forwarded the equivalent result a
second time; the source failed closed and quarantined it.

The resolved workload identity is the organization-owned GitHub App
`ai-sdlc-result-writer`, App ID `5100679`, installed only on
`Young-Consultations/portfolio-tasks`. The reviewed target is immutable
`codex-adapter-v3.0.0` at
`0fa11c078b248ea3201f0aa0f2912fce299a7766`, with conformance report
SHA256 `16333cad6ab38c0a799853a0ab32795525d026f98562982b697492f4b2f6ac91`.
Before Codex, the target reuses its authoritative admission gate, mints a
repository-bounded App installation token, verifies the App slug, and runs the
control-plane-owned result credential capability preflight. The App credential
does not enter the Codex adapter environment.

The 3.0.0 receiver accepts only `RESULT_WRITER_PRIVATE_KEY`, mints a fresh
short-lived installation token after target execution, verifies the same App
slug, and passes only that token to the immutable receiver action. The trusted
result author is `ai-sdlc-result-writer[bot]`, disjoint from admission author
`mightyjoe909`. The portfolio projector listens only to
`ai-sdlc-execution-result-v2`; the dedicated credential probe event has no
business-logic consumer.

Issue #85 established that changing the required reusable-workflow secret from
`CODEX_RESULT_TOKEN` to `RESULT_WRITER_PRIVATE_KEY` is a MAJOR interface
change under the approved release policy. The immutable
`codex-adapter-v2.4.6` tag is therefore unused historical candidate evidence,
and no matching `ai-sdlc-v2.4.6` control-plane release is authorized. The
payload contract remains `ai-sdlc-contract/v2`.

The `ai-sdlc-v3.0.0` tag is now published at
`80889ca14b3bef4254d5212f7f801bf9877ddf72`. Publication does not resolve
#83. Before cost-bearing REAL execution, stop new 2.4.5 implementation
dispatch, set portfolio-tasks `PORTFOLIO_RESULT_SENDERS` exactly to
`ai-sdlc-result-writer[bot]`, and require deployed Runtime Preflight to close
the operational gap tracked by #89. Then immutable REAL preflight,
portfolio-tasks consumer adoption, and controlled same-delivery redelivery must
prove one managed draft, no second Codex execution, one trusted receiver effect,
and one source projection before #83 / DEF-0064 can close.

## 3.0.2 current source-consumer and published 3.0.3 state

Portfolio-tasks currently consumes `ai-sdlc-v3.0.2` through its reviewed
source router pin. That cutover followed deployed Runtime Preflight 36640642872
and immutable REAL preflight 36640734704.

The earlier 2.4.5 path remains immutable initial-live-path evidence from REAL
#154. REAL #156 exposed the result-journal identity defect that drove the 3.0.0
App credential repair. REAL #159 exposed DEF-0073 at the receiver; published
3.0.2 repaired that compatibility boundary.

After source adoption, reconciliation run 36666315992 cleared #159's queued
state while preserving the original trusted 3.0.1 admission for logical
delivery `task-b72eaf2503fc3d27c82f8921e8cfbfff`. Inspection before
reauthorization exposed DEF-0086: the 3.0.2 router would regenerate current
release/activation evidence and reject the preserved predecessor admission.

The resolved 3.0.3 architecture treats the first trusted admission as durable
evidence for the logical delivery. Exact same-release full-binding reuse remains
unconditional. Cross-release reuse requires exact
contract/delivery/correlation/source/target identity plus an immutable
target-bound `reusable_admission_releases` policy. Target compatibility must
prove that policy is a subset of the exact pinned receiver compatibility
allowlist. The router re-queries after creating its identity marker and fails
closed on concurrent, ambiguous, malformed, conflicting, or unsupported
admission state before target dispatch.

The matching immutable target is `codex-adapter-v3.0.3` at
`f11852c7f563df16ea4afa9ab75bf766242e7327`, with conformance adapter
revision
`sha256:3932def5d016b7db11869a0520087aeedcd092799e61dc8617be8bb2f020be3f`
and report SHA-256
`a739cd3dde3c05121fbfc5360495880e265b76448b504936b8583b5efa972ec8`.

Published 3.0.3 is attested at `f3229bfa4a06da963cae7c390c6075b4f6c12f7b`, but do not reauthorize #159 until
this publication attestation, deployed Runtime Preflight, immutable REAL
preflight, and portfolio source repin complete. Then require one corrected
terminal projection followed by an unchanged retry that returns
`duplicate-reused` before Codex with no second visible effect.

The broader organization-level cost-bearing prerequisite policy remains owned
by issue #77 and is not silently expanded by 3.0.2.
