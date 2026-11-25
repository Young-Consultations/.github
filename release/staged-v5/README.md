# v5.0.0 release configuration and one-shot canary runbook

Status: **BLOCKED / NOT AUTHORIZED FOR PUBLICATION OR LIVE EXECUTION**. This directory is a review-only overlay, not the deployed release or a tag attestation. Never copy its files into the active release merely because the offline tests pass. No tags, credentials, approval labels, activation, workflows or environment settings are changed by the staging tests.

## Candidate identity

- Consulting-playbook PR #104 merged at `e4328a6ddde2da6e691b8127b01863b659a5537b`; exact reviewed tree `4f3281403243a5446a4e4a0fd5a84af4db0033c3`; [post-merge conformance](https://github.com/Young-Consultations/consulting-playbook/actions/runs/45533333147) passed.
- Published adapter tag `codex-adapter-v5.0.0`; **independently resolved to the reviewed merge commit above**. Report blob `88f2c18e93036dfd039364c872d46233951070ac`; SHA-256 `b4958777139aaae9084943680f72f34a3b107e71a2f80717af3b1e46f16d0ab1`; pin revision `sha256:1002331e88b9e888f538af9997d35168ba88691f98ca3b02952cc28a580e988f`.
- Planned control-plane tag `ai-sdlc-v5.0.0`; **unresolved**. The staged manifest is unpublished with null tag SHA.
- Existing control-plane and adapter v4 tags and active registry remain unchanged; only consulting-playbook is enabled.
- Overlay includes package/version, router/receiver self-pins, manifest, registry, role manifest, receiver compatibility and generated runtime. Exact committed report and pin are retained as read-only evidence. Candidate registry binds the independently verified immutable adapter tag; binding.json explicitly denies production readiness while the control plane is unpublished.
- Deliberate proposed policy: accept/reuse only v5 admission releases on the new consulting path. Drain and reconcile in-flight v4 work before cutover; do not replay old #167/#170 or other terminal deliveries. Older disabled targets retain exact registry entries and their own frozen receiver refs. This is not a migration of old pending deliveries. The approved #82 deny-only rollback policy replaces previous_known_good in the v5 overlay: no-reviewed-safe-rollback, null candidate, false resume authority. Historical identities remain evidence only; do not use 2.4.4 or v4.0.0 to bypass this gate. If rollback is needed, hold dispatch and prepare separately reviewed recovery composition; no automatic recovery.

## Ordered publication and adoption (separate approvals required)

1. Verify no pending paid approvals or in-flight cost-bearing deliveries; hold new approvals through cutover. Review remaining unsafe rollback/replay exposure. Do not change activation.
2. With separate tag authorization only: verify exact merged adapter, CI and unused tag name; create immutable adapter tag. Independently resolve tag and retrieve raw report/pin; compare binding.json commit, digest, revision and blob hashes. Any mismatch stops. Never retag.
3. Prepare actual control-plane candidate PR from reviewed overlay after independently resolving target binding. Reconcile all current release-specific tests, scripts/run_tc_mvp_e2e_001.py constants and immutable REAL-readiness workflow ref, current release docs, credential scope enforcement (including absence of repository/org fallback for protected readiness/policy values), and the strict deny-only rollback policy (verify manifest/runtime agreement and offline recovery denial; no legacy predecessor field). The overlay contains configuration only; executable migrations are separate candidate changes and require exact-head CI and independent review. Regenerate runtime and run structural and candidate-ready validation, all-target compatibility including release-aware receiver validation, full CI, Actionlint, verify-mode smoke and zero-effect SIM. Require independent review. Published gate must reject unpublished candidate. Do not claim real capability based on structural validation.
4. With separate approval, merge exact candidate, recheck identity and publish immutable control-plane tag; separately attest resolved commit and regenerate runtime. Keep source at v4 and paid approvals withheld until the new exact configuration is verified. Do not permit either old or new dispatch during environment binding changes.
5. Review and separately approve protected environment configuration and no-model canary. After successful owner-reviewed evidence, separately approve protected readiness provisioning, source migration, deployed Runtime Preflight and immutable REAL readiness. These checks do not authorize a paid dispatch. Close #77 only after governed acceptance and ledger reconciliation.

## Preconditions for the live canary

The workflow is `.github/workflows/publication-canary.yml` at the exact immutable target tag, manual only. It checks published control-plane runtime attestation and immutable registry before using the publisher. No OpenAI key, result writer, router or production delivery receipt. Existing publisher must be a user-bound credential whose GitHub /user login can be verified. The required capability is creating a draft PR using that exact credential; no permission widening is part of this plan. The canary creates one Git Data tree/commit and an atomic create-only ref rather than a normal push. Existing per-delivery dry-run push still proves Git transport.

Before approving a run:
- Verify protected environment `consulting-playbook-codex` reviewer/ref restrictions, owner authority, no duplicate repository/org fallback for new values, exact publisher storage and scope, and no paid review, deployment or other external automation triggered by the canary branch/PR. GitHub draft status alone does not prove no paid automation. If this cannot be established, do not dispatch.
- Confirm target and control-plane tags resolve to reviewed commits, the control-plane main runtime attests that exact release and consulting registry, target main base has not moved, no active cost-bearing delivery, and canary ID has never been used. Choose a new stable ID matching [a-z0-9][a-z0-9-]{0,39}; record it in the approval evidence. Never reuse an identity after cleanup.
- Under separately approved environment changes only, set the following protected variables; no values are set by this PR. The first two must match the real owner and publisher logins, not guesses.

| Environment variable | Required value |
| --- | --- |
| PUBLICATION_CANARY_APPROVER | Authorized owner GitHub login |
| PUBLICATION_CANARY_PUBLISHER | Verified actual user login of TARGET_PUBLICATION_TOKEN |
| CODEX_AUTHORIZED_CONTROL_PLANE_SHA | Attested immutable control-plane commit |
| PUBLICATION_POLICY_REVISION | Owner-selected revision matching policy/configuration |
| PUBLICATION_CANARY_AUTHORIZATION | automation-safe:ID:ADAPTER_SHA:CONTROL_SHA:BASE_SHA:POLICY_REVISION:PUBLISHER_LOGIN |

The last variable is an owner attestation that automation and the exact tuple were reviewed. Do not create a broad reusable authorization or substitute a token after approval. The one-shot authorization variables are deliberately not mandatory ongoing runtime metadata roles; revoke authorization separately after use so normal runtime does not depend on an active canary grant.

## Future dispatch procedure (DO NOT RUN NOW)

After explicit separate approval of the precise configuration and side effects, the operator may use GitHub Actions UI or the following command template. Replace ID and BASE_SHA with the approved values; no secrets on the command line.

```bash
gh workflow run publication-canary.yml \
  --repo Young-Consultations/consulting-playbook \
  --ref codex-adapter-v5.0.0 \
  -f canary_id=APPROVED_ID \
  -f base_sha=APPROVED_MAIN_SHA \
  -f confirmation=publish-one-draft
```

Review the protected environment approval before release to the runner. Verify exact run attempt 1, correct immutable workflow SHA, actor and safe status. No automatic retry. Keep at most one canary branch and one draft PR; never mark ready, merge, request review or delete from automation.

## Evidence acceptance and failure handling

Only fresh `created-draft-verified` plus independent operator readback supports current capability attestation. `verified-existing-draft` and `reconciled-draft-not-fresh-proof` establish ownership, not current PR-write capability. Confirm draft open, exact marker-only diff, one parent at approved base, expected author, head/base and repository, immutable release and policy tuple. All output remains readiness_eligible=false until owner decision; no token/fingerprint in logs or Git.

Any denial, unreadable evidence, mismatch, uncertain ref or uncertain PR stops. Read-only reconciliation only; even an empty PR read does not authorize another create if the owned branch exists. Never delete a reservation to retry the same ID. A failure may leave unreachable Git objects or a branch/draft. Preserve evidence and use separate human cleanup approval. On ambiguous stored result, do not accept it as fresh readiness; decide whether a separately approved new canary is appropriate.

After fresh proof, separately approve constructing the v1 PUBLICATION_READINESS_EVIDENCE secret in the protected environment. Use the exact same publisher token's SHA-256 in a secure local process; do not print or commit it. If the operator cannot establish that exact credential, stop, do not guess; separately authorized rotation and new proof are required. Include version=1, repository, executor_sha, control_plane_sha, environment, receiver_ref, policy_revision, credential_sha256, verified_at UTC, outcome=draft-pr-created and exact draft_url. Verify no fallback and no rotation/policy change since proof. Maximum age 30 days; invalidate on drift or suspicion. Record only safe links/identities in issue #77. No automatic cleanup, provisioning or model execution.

## Residual risks

Offline transport tests do not prove actual GitHub permissions, protected variable precedence, automation side effects, eventual consistency or future service availability. The current transport's strict existing-branch stop is intentional. The canary output is not cryptographic proof of token continuity; operator attestation must establish it. Runtime audit must explicitly verify environment scope before adoption. A staged structural PASS is not release readiness.
