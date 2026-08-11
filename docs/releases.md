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

1. Create a focused pull request updating implementation, documentation,
   package version, and manifest together. Run `python scripts/validate_release.py`,
   the complete test suite, registry validation, YAML validation, actionlint,
   and `git diff --check`.
2. Run `python scripts/verify_target_workflows.py` with the router token. Every
   target enabled by current activation state must pass; movable target refs must be replaced with
   reviewed, non-moving `codex-adapter-vMAJOR.MINOR.PATCH` tags before approval.
   Run the Router smoke test in `verify` mode, confirming it invokes
   no Codex runtime and creates no branch or pull request.
3. Obtain protected-branch checks and maintainer approval. Never bypass existing
   approval controls. Merge the reviewed change before tagging.
4. From the reviewed merge commit, re-run the gates, confirm the manifest tag is
   unused, then create and push one annotated `ai-sdlc-vX.Y.Z` tag. Never move,
   delete, or recreate a published tag. This task prepares the lifecycle only;
   it creates no production tag and publishes no Python distribution.
5. Consumers pin the router to that exact tag or, before tag approval, the
   reviewed 40-character merge SHA. Package consumers pin exactly the manifest
   package version and schema consumers retrieve the same tag or SHA.

The candidate contents never name their own future merge SHA. Finalize and
merge first, obtain the immutable commit identity second, and record the pin in
each consumer's own configuration or documentation. This avoids a recursive
release update.

The 2.3.0 receiver and fixture baseline does not embed a prospective commit SHA.
After merge, consumers may pin the resulting 40-character merge SHA; a release
owner may later publish the declared `ai-sdlc-v2.3.0` tag through the governed
process. Activation changes are separate operational changes and do not require
consumers to repin that compatibility SHA. The tag has not been published. A published
`ai-sdlc-contracts==2.3.0` distribution has also not been verified, so MVP
consumers must retrieve the canonical schemas directly at the approved SHA
rather than require that package.

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

The `ai-sdlc-v2.3.0` candidate adds the receiver implementation and complete TC-MVP-CI-001 fixture oracle without enabling a target. Consumers must pin the published tag or the resulting reviewed merge commit; `@main` is never a compatibility unit.

## Rollback

Stop new dispatches through the normal approval control, then change each
consumer pin back to `previous_known_good.commit_sha` from the manifest in
reviewed, repository-local pull requests. Restore package and schema pins from
that same unit; mixing versions is unsupported. Re-run contract tests, every
registered target check, and the verify-mode smoke test before resuming. Do not
move the failed tag and do not weaken the allowlist. The first managed release
records the pre-versioning known-good commit as its rollback point. A corrective
PATCH release updates `previous_known_good` to the last successful release.

### 2.3.0 receiver rollback

Disable result calls and target dispatch first. Re-pin consumers to the 2.2.0
known-good commit in the release manifest, revoke the result-only credential,
and retain admission/result journal comments for reconciliation. Do not delete
receipts or reinterpret an acknowledged transport as execution success. Re-run
the offline fixture harness and receiver tests before restoring dispatch.
