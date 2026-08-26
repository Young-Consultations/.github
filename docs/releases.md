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
4. In the final release pull request, record the reviewed journal-author
   identities, set `tag_published` to `true`, and run
   `python scripts/validate_release.py --require-publishable`. In this lifecycle,
   `tag_published: true` is the reviewed publication-state marker authorizing the
   release to proceed to the immutable-tag step; it does not by itself prove the
   Git tag already exists. Actual tag existence is checked separately after the
   reviewed merge and before REAL acceptance. Obtain protected-branch checks and
   maintainer/security approval. Never bypass existing approval controls. Merge
   the reviewed change before tagging.
5. From the reviewed merge commit, re-run the release-aware target verification,
   release validation, complete test suite, and verify-mode Router smoke test.
   Confirm the manifest tag is still unused, then create and push one annotated
   `ai-sdlc-vX.Y.Z` tag. Never move, delete, or recreate a published tag. After
   tag creation, re-run verification so the same checks resolve the immutable
   tag remotely. This task prepares the lifecycle only; it creates no production
   tag and publishes no Python distribution.
6. Consumers pin the router/receiver to that exact tag or, before tag approval,
   the reviewed 40-character merge SHA where the consumer contract permits it.
   Package consumers pin exactly the manifest package version and schema
   consumers retrieve the same release unit.

The candidate contents never name their own future merge SHA. Finalize and
merge first, obtain the immutable commit identity second, and record the pin in
each consumer's own configuration or documentation. This avoids a recursive
release update. Target conformance follows the same rule: the report records the
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

Published `ai-sdlc-v2.3.2` remains the previous-known-good release at commit
`5738ace3ee90dde11336f8f8099e64e5645f7139`.

PR #54 prepared the `ai-sdlc-v2.4.0` candidate after
`TC-MVP-E2E-001-SIM` exposed DEF-0032. The published receiver rejected every
non-identical second result for one `delivery_id`, while a conforming target
legitimately reports `draft-pr-created` on first success and
`duplicate-reused` when the same managed draft is discovered on redelivery.
The 2.4.0 candidate adds one backward-compatible receiver outcome: that specific
transition is accepted as an idempotent no-op only when the stable managed-draft
effect is unchanged. Every other non-identical result remains ambiguous and
fails closed.

This is a MINOR candidate rather than PATCH because the receiver gains new
observable accepted behavior even though the closed v2 payload schemas and
existing successful calls remain compatible. The final release review sets the
manifest publication-state marker only after target conformance and registry
binding are complete; the immutable tag is still created only after that final
review merges and all release gates pass.

Before 2.4.0 publication, `consulting-playbook` must consume the corrected
receiver through a separately reviewed immutable target adapter, publish fresh
no-real-effects conformance evidence, and be rebound in the registry to that
adapter tag/commit/report digest. Those target and registry steps are complete.
The final release change must pass `python scripts/validate_release.py
--require-publishable`, release-aware registered-target verification, and the
verify-mode Router smoke test. Until the immutable `ai-sdlc-v2.4.0` tag actually
exists and REAL preflight passes, no real acceptance Codex run is authorized.

## Rollback

Stop new dispatches through the normal approval control, then change each
affected consumer pin back to `previous_known_good.commit_sha` from the manifest
in reviewed, repository-local pull requests. Restore package and schema pins
from that same unit; mixing versions is unsupported. Re-run contract tests,
every registered target check, and the verify-mode smoke test before resuming.
Do not move the failed tag and do not weaken the allowlist.

### 2.4.0 candidate rollback

If the 2.4.0 candidate fails before publication, do not create its tag. Restore
the control-plane manifest/receiver/package references to published 2.3.2 and
leave any candidate target adapter tags unused or retained only as immutable
forensic evidence according to repository policy. If 2.4.0 is published and a
post-publication issue is found, stop dispatch first and use the manifest's
`previous_known_good` 2.3.2 commit as the rollback unit through reviewed
repository-local changes. Preserve admission/result journal evidence for
reconciliation; do not delete receipts or reinterpret transport acknowledgement
as execution success.
