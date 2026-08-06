# External Interface Requirements

## External interface catalog

| ID / system | Purpose and data exchanged | Authentication | Failure behavior | Security expectations |
| --- | --- | --- | --- | --- |
| EI-01 GitHub repositories | System of record for code, issues, PRs, reviews, configuration, and immutable refs | GitHub identity and scoped app/token | Preserve state; return diagnosable failure; never infer success | Repository allowlist, protected branches/environments, audit retention |
| EI-02 GitHub Actions | Validate, route, verify, and coordinate target workflows; exchanges event metadata, inputs, outputs, logs, artifacts | `GITHUB_TOKEN`, GitHub App, or approved scoped credential; OIDC for external resources | Timeout/rerun is not proof of non-delivery; retries retain delivery identity | Pin actions immutably, minimal job permissions, untrusted input isolation, no secrets in logs |
| EI-03 GitHub API | Read authoritative state and dispatch registered workflows | Least-privilege short-lived credential | Rate limits, network faults, and ambiguous acknowledgement fail safe; retry with backoff/idempotency | Validate responses, constrain endpoints/repos, audit calls, rotate/revoke credentials |
| EI-04 GitHub Issues | Source task identity, approval/provenance, status and human diagnostics | Authorized GitHub actor/workflow | Missing/edited/ambiguous approval blocks execution | Durable links, edit history awareness, sanitized comments, no secret content |
| EI-05 GitHub Projects | Planning/reporting projection only | Scoped GitHub identity | Project failure must not create or approve work | Project fields cannot independently authorize execution |
| EI-06 GitHub Discussions | Optional non-authoritative discovery/support | GitHub identity | No operational effect | Never treat discussion content as approval or executable instructions |
| EI-07 GitHub Releases/tags | Publish immutable compatibility units and notes | Authorized release maintainer, protected environment | Existing/mismatched tag blocks release; rollback uses known-good immutable pin | Signed release/tag where supported, provenance, checksums/attestations, no tag mutation |
| EI-08 GitHub Packages/artifacts | Optional distribution and evidence transport | OIDC or scoped package token | Missing/integrity-failed object blocks adoption | Digest verification, retention, access controls, SBOM/provenance |
| EI-09 OpenAI/Codex | Target-owned bounded execution from authorized minimized input; prompts, repository context, results | Target-owned approved secret or federated credential | Provider failure produces no fabricated success; target reports sanitized canonical failure | Contractual data controls, minimum retention, no control-plane credential exposure, human review |
| EI-10 ChatGPT | Human-assisted planning that may produce structured proposals, never direct authorization | User/provider identity outside control-plane trust | Unavailable or malformed output remains a proposal | Humans validate; no secrets; provenance retained when promoted to a task |
| EI-11 future AI providers | Provider-neutral bounded execution after governance review | Short-lived, provider-specific least privilege | Isolate provider and fail closed | Security/privacy/legal review, capability profile, egress controls, auditable model/version |
| EI-12 third-party tools | Scanning, notifications, observability, signing, or policy services | Prefer OIDC/GitHub App; avoid long-lived shared secrets | Non-critical tools degrade visibly; mandatory gates block safely | Vendor review, data minimization, regional/retention requirements, revocation and exit plan |

## External interaction requirements

**GH-ER-001 (Must).** Every external integration shall have a named owner, approved purpose, minimum data set, authentication method, permission inventory, retention classification, failure policy, and offboarding procedure. Acceptance: the integration inventory contains all fields and unowned integrations cannot run. Source: V-PRIN/V-GUARD. Verification: document review and negative policy test. Trace: BG-05; RTM; future `TC-ER-001`.

**GH-ER-002 (Must).** External outputs shall be treated as untrusted until their identity, integrity, version, and schema are validated. Acceptance: malformed, unsigned where signing is required, incompatible, or unexpected responses cause no execution. Source: V-PRIN. Verification: interface fault injection. Trace: BG-01/BG-05; `TC-ER-002`.

**GH-ER-003 (Must).** AI-service use shall preserve human approval, minimize transmitted data, prohibit secret transmission, record provider/model identity where available, and return proposed changes only through target-owned draft-PR flow. Acceptance: threat-model scenarios demonstrate no provider can approve, merge, deploy, or obtain control-plane credentials. Source: V-FLOW/V-GUARD. Verification: threat-model and permission review. Trace: BG-02/BG-05; `TC-ER-003`.

**GH-ER-004 (Should).** Mandatory external dependencies shall expose health and actionable failure state without disclosing sensitive values. Acceptance: simulated outage/rate limit is visible and recoverable without log secrets. Source: V-RESP/V-GUARD. Verification: resilience exercise and log scan. Trace: BG-04/BG-05; `TC-ER-004`.
