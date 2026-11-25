# Cost-bearing executor prerequisite policy (issue #77)

Owner approved the narrowed policy on 2026-11-24. Implementation/adoption and live capability testing remain separately governed. Existing immutable releases do not change.

## Mandatory boundary

Before a new cost-bearing model invocation, the target shall establish current evidence that the required publication and result-delivery capabilities are available for the admitted repository, immutable execution release and credential configuration. Failed, missing, stale or indeterminate prerequisite evidence shall prevent model execution. Where read-only verification cannot establish a required capability, a separately authorized bounded no-model capability test may establish readiness. Verification does not authorize further execution, merge, deployment or unrestricted cleanup.

This policy is about sufficient current evidence, not a guarantee of future service availability. Preserve human admission, terminal-receipt denial, verified managed-draft reuse, verify-only behavior, draft-only publication and release identity.

| Boundary | Owner | Evidence |
| --- | --- | --- |
| Authorized target, executor and current content | Router/target | Existing immutable bindings and per-execution workbase attestation |
| Terminal receipt and result delivery | Organization/target | Existing bound journal, scoped result-writer identity, reversible issue-write and no-op dispatch probe per delivery; reviewed sender binding |
| Branch write | Target | Existing authenticated push metadata and dry-run per execution |
| Draft PR creation | Target and operator | Current protected owner-attested successful no-model draft publication evidence for the same publisher credential and configuration |
| Candidate validation, provider startup | Target | Existing sandbox/readiness and validation checks; not a guarantee of provider availability |

## Initial readiness record v1

The initial consulting candidate checks a small JSON record sourced only from the owner-managed protected environment secret `PUBLICATION_READINESS_EVIDENCE`. Never place the record in task input, repository content, logs or model environment. The record is an operator attestation, not independently authenticated GitHub event evidence; the operator must verify the real capability and binding before setting it. A matching token hash alone is not proof of PR creation.

Required fields: integer `version=1`; repository; executor_sha; control_plane_sha; environment; receiver_ref; policy_revision; credential_sha256 (SHA-256 of the exact publisher token); verified_at (UTC timestamp, YYYY-MM-DDTHH:MM:SSZ); outcome (draft-pr-created); draft_url (same repository). The runtime compares the exact token fingerprint, authorized executor and control-plane SHA, receiver ref, environment and owner-controlled protected `PUBLICATION_POLICY_REVISION`. Do not place the token or its fingerprint in Git. Never print evidence. No scope or secret changes are authorized by this candidate.

Maximum age: 30 days (initial operational default). Token rotation and binding changes invalidate immediately. Operator must change the policy revision or remove evidence when repository/branch/environment policy or publisher permissions change, or readiness becomes suspect; the gate does not detect remote permission/policy changes independently. No stale evidence override. Verify-only and proven owned-draft reuse do not require new model authorization.

## Separately approved canary

No live canary is included or authorized. For a later explicitly approved test, use the exact intended publisher credential and protected release configuration, a unique deterministic test branch, harmless change and one draft PR; inspect returned identity and metadata; retain artifacts for operator cleanup; never merge. Do not create a PR per task. No automatic cleanup or repeated model calls. On denied or ambiguous publication, retain evidence and reconcile ownership before any retry. The current production publication retry implementation is not changed by this gate and remains a separate recovery-hardening concern.

## Verification and adoption

Shared `scripts/publication_readiness.py` and `scripts/test_publication_readiness.py` define the minimal evidence check and credential-free test suite; the consulting candidate carries byte-identical copies and binds them in its conformance pin. Test invalid/denied/missing/stale/rotated/mismatched evidence, result receiver unavailable, branch write denied, ownership ambiguity and a valid synthetic positive control with zero actual model and publication calls. Existing immutable TC-MVP-CI-001 fixture version stays unchanged. Candidate conformance is not a live readiness claim.

Only consulting-playbook is in the first implementation scope. The three older registered adapters remain disabled until separately migrated and verified. Review and release coordination, actual protected record provisioning, and separate canary approval precede adoption. No existing release, registry, activation, credentials or Pi services change.
