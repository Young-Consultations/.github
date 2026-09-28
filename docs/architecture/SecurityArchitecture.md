# Security Architecture

## Security objectives

Preserve human authority, repository isolation, least privilege, payload/evidence integrity, confidential data minimization, and attributable decisions. A credential authenticates an actor but does not itself prove approval or authorize arbitrary targets.

## Trust boundaries

```mermaid
flowchart LR
  P[Planning trust domain] -->|untrusted canonical task + provenance| C[Control-plane policy domain]
  R[Reviewed registry/release] -->|validated snapshot| C
  C -->|scoped authenticated dispatch| G[GitHub platform boundary]
  G -->|untrusted delivery| T[Target trust domain]
  T -->|untrusted result/evidence| C
  T -->|minimized prompt| A[AI provider boundary]
```

Every arrow requires identity, integrity, version, authorization and semantic validation.

## Authentication and authorization

- Prefer short-lived workload identity or narrowly scoped app/repository tokens; never pass control-plane credentials to targets or AI providers.
- Authorize caller, authoritative task/approval, target, workflow, mode, task type, contract/release, and scope independently.
- Separate read-only validation/compatibility credentials from dispatch credentials; only the dispatch adapter receives the latter.
- The result receiver loads trusted journal-author identities from
  `config/codex-result-trust.json` through a self-pinned composite action at the
  same immutable control-plane commit as the reusable workflow. It never uses
  caller-associated workflow context to select policy. Targets supply only the
  result-delivery credential and cannot add, replace, or inherit the author
  allowlist. Empty or invalid policy denies all results.
- For the 3.0.0 result path, the dedicated workload identity is GitHub App
  `ai-sdlc-result-writer` (App ID `5100679`), installed only on
  `Young-Consultations/portfolio-tasks`. The enabled target may access its
  private key only as `AI_SDLC_RESULT_WRITER_PRIVATE_KEY` and uses it to mint
  a short-lived installation token scoped to that repository with only Issues
  write and Contents write. The App private key and installation token must not
  enter the Codex adapter environment. The reusable receiver accepts only
  `RESULT_WRITER_PRIVATE_KEY`, mints a fresh installation token after target
  execution, verifies the App slug, and passes only the short-lived token to the
  immutable receiver action.
- The GitHub principal authenticated by the result-delivery token must exactly
  match a reviewed `trusted_result_authors` identity and must remain distinct
  from every trusted admission author. For 3.0.0 the reviewed identity is
  `ai-sdlc-result-writer[bot]`. A control-plane-owned
  credential preflight verifies the runtime identity and required source write
  capabilities before cost-bearing execution by creating and deleting one
  marker comment and sending a dedicated no-consumer repository-dispatch
  probe. The portfolio source projector listens only for
  `ai-sdlc-execution-result-v2`, so
  `ai-sdlc-result-credential-preflight-v1` is not a business-logic trigger. The comment response supplies GitHub's authoritative author identity,
  so both user-bound and GitHub App installation credentials are supported
  without exposing token material. The receiver repeats the reversible
  comment-author check before any result-journal mutation. Any identity,
  issue-write, cleanup, or dispatch-capability mismatch fails closed.
- Govern registry enablement, workflow permissions, security policy and releases with designated independent human review and verified identities where supported.
- Protected default branches and environments enforce that automation cannot clear draft status, merge, deploy, or change settings.

- The source projector sender allowlist is part of the result trust boundary.
  For the 3.0.0 path, `PORTFOLIO_RESULT_SENDERS` must exactly match the
  immutable `trusted_result_authors` set before REAL execution. Runtime
  Preflight verifies this operational value with the audit credential; mere
  variable existence is insufficient. This prevents a post-Codex projection
  failure or retention of an obsolete sender identity.

- Runtime Preflight audits credential availability at the credential's reviewed
  storage scope without reading secret values. Repository and environment
  secrets use their repository-scoped metadata endpoints. A required repository
  role may also be satisfied by an organization Actions secret only when the
  organization matches the repository owner, the secret visibility is
  `selected`, and the exact repository is in that selected set. Broader
  organization-secret visibility does not satisfy this boundary. The
  `PREFLIGHT_AUDIT_TOKEN` therefore requires read access to organization
  Actions secret metadata and selected-repository access in addition to the
  existing repository/environment metadata reads.

## Secrets and data protection

Secrets live in an approved secret service/environment, are never embedded in contracts, prompts, source, logs, artifacts or diagnostics, and are rotated/revoked on exposure or offboarding. Classify/minimize payloads; prohibit secrets and disallowed personal/confidential data; sanitize failure messages; apply least-access retention/deletion to prompts, logs, artifacts and results.

## Integrity, auditability and confidentiality

Pin third-party automation by immutable identity and verify release/schema/package digests. Preserve actor, authoritative source, approval, release/registry identity, delivery/attempt identity, policy decision, permission context, target result and human review as tamper-evident references. Restrict raw evidence while exposing safe metadata. Signing is required where reliable organization enforcement exists; exceptions need explicit risk acceptance.

## Threat considerations

| Threat | Control |
| --- | --- |
| Forged/stale approval | Verify authoritative provenance, actor and freshness; fail closed. |
| Confused deputy/arbitrary target | Allowlisted exact repository/workflow and scoped credential. |
| Payload/schema smuggling | Closed schemas, format/invariant validation on both sides. |
| Prompt injection/scope expansion | Treat task text as data; bounded scope; target policy; no credential/tool authority from prose. |
| Duplicate/race publication | Stable delivery ID, deterministic marker/branch, preflight, requery, ambiguity rejection. |
| Supply-chain compromise | Immutable action/dependency pins, scanning, protected updates, release integrity. |
| Secret leakage | Minimization, redaction, log scanning, access/retention policy. |
| False success/evidence substitution | Authenticated correlated target evidence; absence/conflict is not success. |
| Caller-controlled journal trust | Immutable control-plane author allowlist; target-supplied trust fields or secrets are rejected. |
| Privilege escalation via PR | Draft-only publication, protected branches, human review, no auto-merge. |

Security tests include negative authorization, permissions, secret canaries, dependency/action integrity, malformed contracts, concurrency, evidence substitution and provider-boundary threat scenarios.
