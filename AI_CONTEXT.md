# AI Context

This file is the ordered entry point for AI tools and developers working in the `Young-Consultations/.github` repository.
Read the sections below in order before proposing or implementing changes. Follow the linked canonical sources rather than treating this index as a replacement for contracts, schemas, workflows, architecture decisions, or repository policy.

## 1. Vision

Read these sources in order:

1. [Young Consultations AI-SDLC vision](docs/VISION.md) — authoritative for
   organization and `Young-Consultations/.github` intent, boundaries, guiding
   principles, and the handoff to requirements development.
2. [Epic 1 — Stabilize the AI-SDLC control plane](https://github.com/Young-Consultations/portfolio-tasks/issues/72)
   — defines the approved control-plane stabilization work and completion
   criteria in the organization backlog.

The vision document is authoritative for intent; it does not assert that
planned capabilities are implemented. Versioned contracts, schemas, the
repository registry, released workflows, tests, and release documentation
remain authoritative for implemented behavior. Where vision and current
behavior differ, describe the gap rather than treating intent as implementation.

`Young-Consultations/portfolio-tasks` remains the authoritative backlog, planning, and approval source. GitHub Projects may report task state but is not an executable task source.

## 2. Current project state

The current project state is tracked through authoritative GitHub issues rather than duplicated in this repository.

- [Epic 1 — Stabilize the AI-SDLC control plane](https://github.com/Young-Consultations/portfolio-tasks/issues/72) — parent stabilization epic.
- [Issue 80 — Create AI_CONTEXT.md for organization .github](https://github.com/Young-Consultations/portfolio-tasks/issues/80) — source task for this context index.

Review the parent epic and its linked child issues before making changes that affect contracts, routing, execution ownership, security boundaries, or repository integrations.

## 3. Architecture

Read these sources in order:

1. [Young Consultations AI-SDLC vision](docs/VISION.md) — establishes intent
   and ownership boundaries; it is not an implementation specification.
2. [Repository README](README.md) — defines the AI-SDLC platform repository, contract-validation package, verification sequence, and platform-versus-execution ownership boundary.
3. [Organization Codex router](docs/codex-router.md) — defines router responsibilities, canonical routing, execution modes, concurrency, registry policy, failure categories, workflow ownership, and verification stages.
4. [Canonical contracts](contracts/) — authoritative schemas and contract examples used by planning, routing, execution, and result reporting.
5. [Repository registry](config/codex-repositories.json) — authoritative allowlist and shared routing policy for registered target repositories.
6. [Organization router workflow](.github/workflows/codex-router.yml) — reusable organization routing boundary.
7. [AI-SDLC contract tests](.github/workflows/ai-sdlc-contract-tests.yml) — canonical read-only contract, schema, registry, router, integration-boundary, and security verification.
8. [Router smoke test](.github/workflows/router-smoke-test.yml) — execution-level verification of the organization router.
9. [Control-plane releases](docs/releases.md) — canonical versioning, release, upgrade, deprecation, and rollback procedure.

### Ownership boundary

`Young-Consultations/.github` owns the shared contracts, schemas, validation package, repository registry, organization router, and shared verification workflows.
The organization router validates and routes approved work. It does not execute repository modifications.
Registered target repositories own their implementation workflows, repository-specific validation, deterministic implementation branches, and draft-pull-request publication.

## 4. Coding standards

No standalone canonical coding-standards document has been identified in this repository.
Until one is adopted:

- follow the conventions already present in the affected Python, JSON, YAML, Markdown, and test files;
- keep changes focused on the approved issue;
- preserve contract and schema compatibility unless the task explicitly authorizes a versioned contract change;
- do not introduce repository-specific parsing into shared contracts or router code;
- validate JSON and YAML syntax;
- run the repository's documented tests and static checks;
- run `git diff --check`;
- do not include credentials, tokens, private URLs, authorization headers, or sensitive configuration.

This section is an explicitly documented gap. Do not create or infer new organization coding policy as part of unrelated work.

## 5. ADRs

No canonical ADR index or ADR directory has been identified in this repository.
Existing architectural behavior must be derived from the authoritative repository documentation, contracts, registry, workflows, tests, and approved portfolio issues listed in this file.
This section is an explicitly documented gap. Do not invent architectural decisions or create retrospective ADRs unless an approved issue specifically requests them.

## 6. Development workflow

Use the following workflow:

1. Start from an approved issue in `Young-Consultations/portfolio-tasks`.
2. Confirm the declared target repository, task type, dependencies, risk, scope, and execution status.
3. Read this `AI_CONTEXT.md` in order.
4. Read all canonical documents relevant to the affected component.
5. Create one focused implementation branch derived from the canonical task identity.
6. Modify only files required by the approved issue.
7. Run the repository's applicable validation and test suite.
8. Run `git diff --check`.
9. Publish exactly one draft pull request against the target repository's default branch.
10. Report the branch, draft pull request, tests, and canonical execution result back through the approved AI-SDLC path.

Automated execution must not:

- merge a pull request;
- push directly to `main`;
- use `pull_request_target`;
- mutate repository or organization settings;
- modify repositories outside the declared target;
- expose credentials or sensitive configuration.

The verification order for shared control-plane changes is:

1. AI-SDLC Contract Tests
2. Router smoke test
3. Registered target-repository execution
4. Full ChatGPT-to-draft-PR end-to-end verification

## 7. Prompt rules

No standalone canonical prompt-rules document has been identified in this repository.
Until one is adopted, AI tools must follow these repository-specific rules:

- Treat approved portfolio issue fields as the implementation boundary.
- Do not expand scope beyond the issue's objective, requirements, acceptance criteria, and explicitly listed files or components.
- Inspect repository documentation before making assumptions.
- When repository documentation does not answer a material question, state the gap rather than inventing policy.
- Prefer canonical contracts, schemas, registry entries, workflows, tests, and approved issues over summaries or generated prose.
- Preserve deterministic task, correlation, branch, and draft-PR behavior.
- Do not weaken repository allowlisting, least privilege, token redaction, dependency checks, contract validation, or draft-only publication.
- Do not add automatic merge behavior.
- Do not duplicate canonical contracts or architecture rules in generated documentation.
- Keep each pull request focused on one approved task.

This section is an explicitly documented gap. A future approved issue may replace it with a link to a canonical prompt-rules document.

## 8. Open issues

Authoritative work is tracked in `Young-Consultations/portfolio-tasks`.
Start with:

- [Epic 1 — Stabilize the AI-SDLC control plane](https://github.com/Young-Consultations/portfolio-tasks/issues/72)
- [Issue 80 — Create AI_CONTEXT.md for organization .github](https://github.com/Young-Consultations/portfolio-tasks/issues/80)

Use GitHub issue state as the source of truth. Do not maintain a copied backlog or manually duplicated issue-status table in this file.

## Maintenance rule

Update this index in the same pull request whenever:

- a linked repository document is moved, renamed, replaced, or removed;
- a previously documented gap receives a canonical document;
- ownership boundaries change through an approved architectural decision;
- a contract release changes the authoritative schema, package, workflow interface, registry format, or compatibility documentation.

For versioned contract releases, update links to the current canonical documentation without copying contract definitions into this file. Historical behavior belongs in release documentation, version history, or ADRs—not in this navigation index.
All relative links in this file must resolve on the repository default branch. All external issue links must point to authoritative `Young-Consultations/portfolio-tasks` issues.
