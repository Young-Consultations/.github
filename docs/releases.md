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
* **MINOR** changes add optional workflow or package APIs, add opt-in router
  behavior without changing existing calls, or make backward-compatible schema
  additions after every registered consumer accepts them. Because schemas are
  closed, producers must not emit an optional addition until compatibility is
  proven. Adding a registered target is minor; removing one is major unless it
  was already formally deprecated.
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

1. Create a focused recovery candidate pull request updating implementation,
   documentation, package version, and manifest together. Run
   `python scripts/validate_release.py`, the complete test suite, registry
   validation, YAML validation, actionlint, and `git diff --check`. Structural
   coherence does not assert publication readiness.
2. Correct each target independently. Publish no adapter tag until its real
   repository adapter passes every shared-oracle scenario with all prohibited
   effects at zero. Bind that report to a canonical v2 conformance pin containing
   exact shared-file and target adapter/harness blob identities. The report must
   not try to embed the SHA of its own containing commit. Then create the
   immutable `codex-adapter-vMAJOR.MINOR.PATCH` tag and record its independently
   resolved commit plus the committed report digest in the capability registry.
3. Explicitly verify every registered target with
   `python scripts/verify_target_workflows.py --repository OWNER/REPOSITORY`.
   The unselected default report treats disabled targets as `not-evaluated` and
   exits nonzero; disabled, skipped, movable, missing, or substituted evidence
   cannot satisfy release approval. Run the Router smoke test in `verify` mode,
   confirming it invokes no Codex runtime and creates no branch or pull request.
4. In the final release pull request, record the reviewed journal-author
   identities, set `tag_published` to `true`, and run
   `python scripts/validate_release.py --require-publishable`. Obtain
   protected-branch checks and maintainer/security approval. Never bypass
   existing approval controls. Merge the reviewed change before tagging.
5. From the reviewed merge commit, re-run the gates, confirm the manifest tag is
   unused, then create and push one annotated `ai-sdlc-vX.Y.Z` tag. Never move,
   delete, or recreate a published tag. This task prepares the lifecycle only;
   it creates no production tag and publishes no Python distribution.
6. Consumers pin the router to that exact tag or, before tag approval, the
   reviewed 40-character merge SHA. Package consumers pin exactly the manifest
   package version and schema consumers retrieve the same tag or SHA.

The candidate contents never name their own future merge SHA. Finalize and
merge first, obtain the immutable commit identity second, and record the pin in
each consumer's own configuration or documentation. This avoids a recursive
release update. Target conformance follows the same rule: the report records the
non-recursive conformance-pin revision, while the later registry entry records
the tag's resolved commit and report digest.

Reviewed 2.3.0 commit
`c6090e5bbadcc2102a1cb91875466e9decdada1e` remains immutable historical
evidence. It is not rewritten, retagged, or treated as activation-safe. The
2.3.1 recovery candidate does not embed its prospective merge SHA and leaves
`tag_published: false`, every target disabled with pending conformance, and the
receiver author allowlist empty/deny-all. Those conditions deliberately make
`--require-publishable` fail. After the target sequence and final release review,
consumers may pin the corrected merge SHA or published `ai-sdlc-v2.3.1` tag.
Activation remains a separate operational change and does not require
repinning. No `ai-sdlc-contracts==2.3.1` distribution is claimed until actually
published and verified.

Production mode remains draft-only. Release validation does not dispatch work,
change settings or secrets, widen permissions, or create an approval bypass.

## Upgrade, deprecation, and consumer coordination

Upgrade a consumer in its own pull request: update immutable router and
schema/package pins as one change, validate its reusable-workflow call against
the manifest, run repository tests, then run organization target compatibility.
Do not update an unregistered repository.

Deprecations are announced at least one MINOR release before removal and remain
supported for at least 90 days. Removal occurs only in a MAJOR release after all
registered consumers migrate. Critical security remediation may shorten the
window only with an explicit risk record and maintainer approval. Pre-releases
do not start the window.

The four registered consumers—`.github`, `portfolio-tasks`, `consulting-playbook`, and
`slugger`—must each replace any mutable organization-router reference in a
separate repository pull request with the new tag (or reviewed merge SHA).
Cross-repository edits are intentionally not combined here. Release approval
must record those three consumer PRs or confirm that no router call exists.

## Current compatibility update

The `ai-sdlc-v2.3.1` recovery candidate corrects the dynamic target interface,
receiver trust ownership, immutable evidence registry, and fail-closed
publishability rules without enabling a target. The PATCH designation records a
security/compatibility repair of the unpublished 2.3.0 candidate; no approved
production backward-compatibility promise is being bypassed. Consumers must pin
the eventual reviewed merge commit or published tag; `@main` is never a
compatibility unit.

## Rollback

Stop new dispatches through the normal approval control, then change each
consumer pin back to `previous_known_good.commit_sha` from the manifest in
reviewed, repository-local pull requests. Restore package and schema pins from
that same unit; mixing versions is unsupported. Re-run contract tests, every
registered target check, and the verify-mode smoke test before resuming. Do not
move the failed tag and do not weaken the allowlist. The first managed release
records the pre-versioning known-good commit as its rollback point. A corrective
PATCH release updates `previous_known_good` to the last successful release.

### 2.3.1 recovery rollback

Disable result calls and target dispatch first. Re-pin consumers to the 2.2.0
known-good commit in the release manifest, revoke the result-only credential,
and retain admission/result journal comments for reconciliation. Do not delete
receipts or reinterpret an acknowledged transport as execution success. Re-run
the offline fixture harness and receiver tests before restoring dispatch.
