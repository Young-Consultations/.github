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
   Merge the attestation before deployed Runtime Preflight or REAL acceptance.
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

Published `ai-sdlc-v3.0.3` is the current control-plane compatibility release
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

Stop new dispatches through the normal approval control before changing release
pins. A manifest `previous_known_good` entry is a rollback candidate, not
automatic authority to resume cost-bearing execution.

Before selecting a rollback release, review the failure class and verify that
the candidate is not known to contain the same affected-path defect. If the
recorded predecessor is known unsafe or rollback safety is indeterminate, keep
REAL implementation disabled and select a separately reviewed safe release.
Do not resume cost-bearing Codex work until that release passes the applicable
contract, target-compatibility, publication, credential, and operational
preflight gates.

For 2.4.5 specifically, the manifest records 2.4.4 as
`previous_known_good`, but REAL #151 proved that 2.4.4 can lose completed Codex
work during publication. Therefore 2.4.4 must not be used to resume cost-bearing
implementation. Issue #82 owns correction of the manifest/rollback-safety
representation; this containment rule applies until that decision is resolved.

When a reviewed safe rollback release is selected, update affected consumer pins
through repository-local pull requests, restore package/schema pins from that
same immutable unit, and rerun all required checks before resuming. Do not move
published tags, mix release units, weaken allowlists, or erase audit evidence.

### Historical 2.4.0 candidate rollback

If the 2.4.0 candidate fails before publication, do not create its tag. Restore
the control-plane manifest/receiver/package references to published 2.3.2 and
leave any candidate target adapter tags unused or retained only as immutable
forensic evidence according to repository policy. If 2.4.0 is published and a
post-publication issue is found, stop dispatch first and use the manifest's
`previous_known_good` 2.3.2 commit as the rollback unit through reviewed
repository-local changes. Preserve admission/result journal evidence for
reconciliation; do not delete receipts or reinterpret transport acknowledgement
as execution success.
