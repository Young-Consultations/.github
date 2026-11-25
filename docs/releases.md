# AI-SDLC control-plane releases

The repository release is one atomic compatibility unit. The current unit is
declared in [the release manifest](../release/release-manifest.json): the router
behavior and reusable-workflow interface, packaged `ai-sdlc-contracts` API,
canonical schemas, capability-registry format and snapshot, and supported-target set all
receive one SemVer release. The immutable tag is
`ai-sdlc-vMAJOR.MINOR.PATCH`; branches are development inputs, never releases.

## Compatibility and SemVer

* **MAJOR** changes remove or rename workflow inputs, outputs, secrets, or
  permissions; expand a required permission; change input/output meaning; break
  a package API; make previously valid schema data invalid; change a closed
  enum; or incompatibly change registry keys or semantics.
* **MINOR** changes add backward-compatible workflow or package behavior,
  optional APIs, opt-in router behavior without breaking existing calls, or
  backward-compatible schema additions after every registered consumer accepts
  them. Because schemas are closed, producers must not emit an optional schema
  addition until compatibility is proven. Adding a registered target is minor;
  removing one is major unless it was already formally deprecated.
* **PATCH** changes fix implementation or documentation without changing the
  accepted interface or observable policy. Security fixes use the level their
  compatibility impact requires; SemVer is not bypassed.
* Pre-releases use suffixes such as `-rc.1`. They are immutable test releases,
  not production recommendations, and cannot replace the known-good release
  until the normal approval and compatibility gate passes.

The payload namespace (`ai-sdlc-contract/vN`) advances for breaking data
changes and may differ numerically from release SemVer. The manifest is the
authoritative mapping. Registry format version 1 permits only the currently
validated keys; changing their meaning is breaking.

## Controlled release procedure

1. Create a focused candidate pull request updating implementation,
   documentation, package version, and manifest together. Run
   `python scripts/validate_release.py`, the complete test suite, registry
   validation, YAML validation, actionlint, and `git diff --check`. Structural
   coherence does not assert publication readiness.
2. Correct each affected target independently. Publish no adapter tag until its
   real repository adapter passes every shared-oracle scenario with all
   prohibited effects at zero. Bind that report to a canonical v2 conformance
   pin containing exact shared-file and target adapter/harness blob identities.
   The report must not try to embed the SHA of its own containing commit. Then
   create the immutable `codex-adapter-vMAJOR.MINOR.PATCH` tag and record its
   independently resolved commit plus the committed report digest in the
   capability registry.
3. Explicitly verify every registered target with
   `python scripts/verify_release_target_workflows.py --repository OWNER/REPOSITORY`.
   Scheduled, manual and PR compatibility checks use the built-in read-only
   Actions token (`GH_TOKEN`); local live checks require an explicitly supplied
   read-only `GH_TOKEN` or `GITHUB_TOKEN`. Never use a router/dispatch token.
   Missing authentication, rate limits and API outages block verification
   (indeterminate evidence), not proof of incompatibility. Run the manual
   compatibility workflow with `repository: all` on the candidate branch to
   verify cross-repository access before acceptance. No activation changes.
   This release-aware command delegates to the normal immutable verifier first.
   Before the control-plane tag exists, it may verify the current reviewed
   checkout only when the target pins the exact tag named by the current release
   manifest and GitHub confirms that exact tag is still absent. The local
   receiver must self-pin that exact manifest tag and its action, trust policy,
   receiver implementation, and result schema must pass the same interface and
   policy checks. Any other missing, movable, substituted, or incompatible ref
   fails closed. After the tag exists, normal remote immutable verification
   takes precedence. The unselected default report treats disabled targets as
   `not-evaluated` and exits nonzero. Run the Router smoke test in `verify` mode,
   confirming it invokes no Codex runtime and creates no branch or pull request.
4. In the candidate pull request, record the reviewed journal-author identities,
   set `tag_published` to `false` and `tag_commit_sha` to `null`, generate the
   candidate runtime record, and run structural release validation plus
   `python scripts/validate_release.py --require-candidate-ready`, the
   release-aware target verifier, complete tests, and verify-mode Router smoke
   test. Obtain protected-branch checks and maintainer/security approval. The
   candidate readiness gate checks all publishable bindings and trusted authors
   while requiring the unpublished manifest state. `--require-publishable`
   must fail for that candidate state.
   Merge the reviewed candidate before tagging.
5. From the reviewed candidate merge commit, re-run those checks and confirm
   the manifest tag is unused. Create and push one immutable `ai-sdlc-vX.Y.Z`
   tag at that exact merge commit. Lightweight and annotated Git tags are both
   acceptable; release identity is the tag name plus its independently resolved
   commit SHA. Never move, delete, or recreate a published
   tag. Then submit a separate publication-attestation pull request that records
   the tag's resolved commit as `tag_commit_sha`, sets `tag_published` to `true`,
   regenerates the runtime record, and passes
   `python scripts/validate_release.py --require-publishable`, remote immutable
   target verification, complete tests, protected-branch checks, and review.
   Merge the attestation before separately reviewed source migration and deployed
   Runtime Preflight. A deployed preflight PASS must independently verify the
   source `portfolio-tasks@main` router job pins the same attested immutable
   control-plane release. While the source still pins a predecessor, the
   deployed preflight must FAIL CLOSED. Candidate/SIM checks are not substitute
   deployed evidence.
   Pre-tag candidate checks and approvals are the authorization to consume the
   immutable version; post-tag attestation proves the resulting identity.
6. Consumers pin the router/receiver to that exact tag or, before tag approval,
   the reviewed 40-character merge SHA where the consumer contract permits it.
   Package consumers pin exactly the manifest package version and schema
   consumers retrieve the same release unit.

The candidate contents never name their own future merge SHA. Finalize and
merge first, obtain the immutable commit identity second, and record it in the
attestation as well as each consumer's own configuration or documentation. This
avoids a recursive release update. Target conformance follows the same rule: the report records the
non-recursive conformance-pin revision, while the later registry entry records
the tag's resolved commit and report digest.

Published `ai-sdlc-v2.3.1` and `ai-sdlc-v2.3.2` remain immutable historical
evidence. Release 2.3.2 repaired incomplete `portfolio-tasks` and `slugger`
conformance bindings by publishing new adapter tags whose pins include the exact
report-producing harness. Subsequent governance review enabled only
`consulting-playbook`; activation remains mutable operational state separate
from immutable compatibility.

Production mode remains draft-only. Release validation does not dispatch work,
change settings or secrets, widen permissions, or create an approval bypass.

## Upgrade, deprecation, and consumer coordination

Upgrade a consumer in its own pull request: update immutable router/receiver and
schema/package pins as applicable, validate its reusable-workflow call against
the manifest, run repository tests, then run organization target compatibility.
Do not update an unregistered repository.

Deprecations are announced at least one MINOR release before removal and remain
supported for at least 90 days. Removal occurs only in a MAJOR release after all
registered consumers migrate. Critical security remediation may shorten the
window only with an explicit risk record and maintainer approval. Pre-releases
do not start the window.

Cross-repository consumer edits are intentionally separate. Release approval
must record the affected consumer/target PRs or confirm that no update is
required for a given registered repository.

## Current compatibility update

Published `ai-sdlc-v4.0.0` resolves to reviewed PR #116 merge commit
`6e51f058bf828b0732cb1b773ba1835acaa1d5cd`. The separate publication attestation
records that SHA and the generated published runtime. The matching immutable
target `codex-adapter-v4.0.0` resolves to
`84964d3ba099630cd5c6101e598bfca5433c74c5`, with report SHA-256
`1eba66061a253c821110c274fdaebfd6442b0ca4fa4acb4f9761c250a6c9c13b`.
V2 payload schemas remain unchanged. Published `ai-sdlc-v4.0.0` at `6e51f058bf828b0732cb1b773ba1835acaa1d5cd` is attested by PR #117. Portfolio PR #169 migrated the source pin to 4.0.0; only `consulting-playbook` is enabled, at immutable `codex-adapter-v4.0.0` (`84964d3ba099630cd5c6101e598bfca5433c74c5`). The deployed Runtime Preflight and immutable REAL readiness passed in runs [40800598820](https://github.com/Young-Consultations/.github/actions/runs/40800598820) and [40800767847](https://github.com/Young-Consultations/.github/actions/runs/40800767847). Fresh [source #171](https://github.com/Young-Consultations/portfolio-tasks/issues/171) and [target run 40802447762](https://github.com/Young-Consultations/consulting-playbook/actions/runs/40802447762) established DEF-0125 executor/current-content separation, one model invocation, one managed draft and correlated result. [Consulting PR #99](https://github.com/Young-Consultations/consulting-playbook/pull/99) merged following review; its [acceptance journal](https://github.com/Young-Consultations/consulting-playbook/blob/main/ai-sdlc/engineering-journal/2026-10-28-def-0125-live-acceptance.md) records the October 28 closure. This is specific live-path evidence, not acceptance of terminal-failure replay (#111), other target activation, or future REAL execution. Never replay finalized sources #167 or #170.



## Runtime Preflight credential recovery

For deployed verification use `runtime-preflight.yml` on `main`, with
`candidate_mode=false`. The built-in Actions token checks the immutable
release tag; `PREFLIGHT_AUDIT_TOKEN` is a separate read-only credential
for required repository/environment/organization metadata, sender binding and
the source router pin. The audit never reads secret values. Metadata PASS
does not prove that every execution credential is valid for its actual role.

If verification fails, inspect the fixed HTTP category and affected scope.
401 indicates rejected authentication (check expiration or revocation); 403
can indicate forbidden access or rate limiting; 404 means the resource is
unavailable or inaccessible; 429 indicates rate limiting; 5xx indicates
service failure. Unknown CLI failures are indeterminate. Do not weaken
verification, retry repeatedly, or substitute router credentials.

For an expired PAT, the owner regenerates it in GitHub's fine-grained PAT
settings, preserving the already reviewed repository selections, read-only
audit permissions and expiration policy. Update the existing secret at its
actual repository or selected-organization scope. Do not add duplicate
secrets, widen permissions, or print values. For an existing repository
secret, an authenticated administrator may use the interactive CLI:

```bash
gh secret set PREFLIGHT_AUDIT_TOKEN --repo Young-Consultations/.github
gh workflow run runtime-preflight.yml --repo Young-Consultations/.github --ref main -f candidate_mode=false
```

Use the existing organization secret settings instead if that is the
approved storage scope. Review credential roles in
[the manifest](../config/codex-credential-roles.json) and
[Security Architecture](architecture/SecurityArchitecture.md).
Do not rotate the GitHub App private key, protected provider secret or
Personal Ops credential as a side effect. Verify every affected role with
its existing least-effect gate before a separately approved REAL delivery.
Record expiration dates without secret material and plan renewal before expiry.

On November 24, 2026, [run 45502035833](https://github.com/Young-Consultations/.github/actions/runs/45502035833)
failed audit metadata and source-pin retrieval; the owner observed an expired
audit PAT. Following renewal, [run 45507185255](https://github.com/Young-Consultations/.github/actions/runs/45507185255)
passed all five boundaries at unchanged main `dd9d4b4fed70d0316d7f84d338ef7041a4e06859`.
This establishes recovery, not new REAL acceptance. A successful deployed
preflight directs the operator to the applicable release acceptance evidence;
run immutable REAL preflight only if readiness remains outstanding. Offline
checks and candidate SIM never authorize REAL.

### Historical 3.1.0 publication

Published and attested `ai-sdlc-v3.1.0` is the preceding immutable control-plane
compatibility release at reviewed PR #113 merge commit
`e9d11fc99fee73d247c93699f058ed64786bd4c0`; separate attestation PR #114
records that identity on `main`. The matching reviewed target is immutable
`codex-adapter-v3.1.0` at
`4f15841efcba4883770b5e32c0582f733d73eb91`, with tagged 29-case
zero-real-effect conformance report SHA-256
`f0a73ed1298e68beb2956c50488dc191fafb28b7b1cce74618e8fb488f076606`.
The receiver supports reviewed admissions 3.0.1, 3.0.2, 3.0.3, and 3.1.0;
the new terminal-receipt preflight rejects re-execution after trusted terminal
failure, limiting prior managed draft results to ownership-verified reuse.
Release and attestation do **not** establish deployed Runtime Preflight, source
adoption or REAL acceptance. At that historical stage the source still pinned 3.0.3 and #93 required assessment. Both have been superseded by the 4.0.0 migration and specific live acceptance above; #111 remains separate.

### Historical 3.0.3 publication and source adoption

Published `ai-sdlc-v3.0.3` remains immutable historical compatibility evidence
at reviewed PR #104 merge commit `f3229bfa4a06da963cae7c390c6075b4f6c12f7b`.
Portfolio-tasks now consumes published 3.0.3 through merged PR #163 at
`580eaf3cd88774014d645d3c3ca3718b39b38ce0`.

3.0.3 repairs #103 / consulting-playbook DEF-0086 by preserving durable
predecessor admission evidence across authorized unchanged retries rather than
regenerating release/activation evidence from the current router.

The matching immutable target is `codex-adapter-v3.0.3` at
`f11852c7f563df16ea4afa9ab75bf766242e7327`, with adapter revision
`sha256:3932def5d016b7db11869a0520087aeedcd092799e61dc8617be8bb2f020be3f`
and report SHA-256
`a739cd3dde3c05121fbfc5360495880e265b76448b504936b8583b5efa972ec8`.

For published 3.0.3, the reviewed receiver/admission compatibility set is:

- `ai-sdlc-v3.0.1`, required to preserve #159's original durable admission;
- `ai-sdlc-v3.0.2`, required for deliveries admitted after the previous source
  cutover; and
- `ai-sdlc-v3.0.3`, required for new admissions after future 3.0.3 adoption.

The target registry declares the same predecessor/current set for cross-release
reuse, and release-aware target verification must prove that set is a subset of
the exact pinned receiver allowlist. Same-release exact-binding reuse does not
depend on the predecessor allowlist.

Before publication, Contract Tests, Target Compatibility, and TC-MVP-E2E-001
SIM passed on the exact reviewed PR #104 head. Lightweight
`ai-sdlc-v3.0.3` resolves exactly to
`f3229bfa4a06da963cae7c390c6075b4f6c12f7b`. After publication attestation,
deployed Runtime Preflight 36867504568 and immutable REAL readiness preflight
36867939797 passed before portfolio-tasks adopted 3.0.3.

Fresh #159 then completed the required live acceptance sequence. First target
run 36911342397 produced one managed draft PR #82 and source run 36911478182
recorded one terminal projection. Unchanged reroute 36913373900 and target run
36913463403 preserved the same delivery/branch/PR and returned
`duplicate-reused` before Codex with no second receiver/source visible effect.

Published 3.0.2, 3.0.1, and 3.0.0 remain immutable predecessor evidence.

## Rollback

GH-FR-015 / ADR-007 / issue #82: stop new implementation dispatch before
changing release pins. Current runtime health and recovery authorization are
distinct. The approved v5 design records `rollback_policy` in the manifest
and generated runtime with state `no-reviewed-safe-rollback`, candidate null
and real_resume_authorized false. No other policy shape is supported by this
slice. Missing, contradictory or malformed policy fails validation. Normal
runtime checks may pass while rollback is unavailable; neither a health check
nor this metadata authorizes execution. The read-only
`python scripts/runtime_preflight.py --rollback-recovery` decision always
denies resume and performs no external checks or mutations. No automatic
rollback exists.

If rollback is necessary, preserve evidence, hold approvals/dispatch, and
review a separate recovery composition (control plane, target, source,
registry, receiver, credentials, publication and applicable acceptance
evidence). Do not resume cost-bearing work until it is independently verified
and separately authorized by the owner. Use reviewed repository-local changes
to restore coherent immutable pins. Never move tags, mix release units, weaken
allowlists, replay terminal deliveries or erase audit evidence.

The immutable v4 and earlier manifests retain historical
`previous_known_good` values. These are **historical identity only**, never
rollback authority. REAL #151 proved 2.4.4 can lose completed Codex work in
publication; neither it nor any other predecessor is selected as safe.
DEF-0105 remains accepted-risk pending operational adoption of the approved
representation. Staged v5 is unpublished and not deployable; all publication
and execution gates remain separate.

### Historical 2.4.0 candidate rollback

Historical procedure retained for forensic context only; it is not current rollback authority. If the 2.4.0 candidate fails before publication, do not create its tag. Restore
the control-plane manifest/receiver/package references to published 2.3.2 and
leave any candidate target adapter tags unused or retained only as immutable
forensic evidence according to repository policy. If 2.4.0 is published and a
post-publication issue is found, stop dispatch first and use the manifest's
`previous_known_good` 2.3.2 commit as the rollback unit through reviewed
repository-local changes. Preserve admission/result journal evidence for
reconciliation; do not delete receipts or reinterpret transport acknowledgement
as execution success.

## v5.0.0 unpublished candidate (V5.3)

The approved adapter tag `codex-adapter-v5.0.0` independently resolves to `e4328a6ddde2da6e691b8127b01863b659a5537b`; the staged binding now records that exact immutable identity. The candidate branch composes the reviewed overlay. It does not change deployed main, source pins, activation, credential configuration, or authorize REAL. Candidate SIM and release-aware compatibility checks are evidence only. The published gate must deny this unpublished manifest. No rollback resume is allowed. Protected publication metadata must have no repository or organization fallback; inability to inspect either scope blocks readiness. DEF-0105 remains accepted-risk for the deployed v4 baseline. DEF-0147 remains investigating until a scheduled compatibility run on the actual accepted main revision verifies the intended registered targets with the read-only built-in token, no missing router credential, and retained reports; PR/synthetic CI is not that scheduled evidence. Do not dispatch operational workflows, publish the control-plane tag, or enable additional targets without separate approval.
