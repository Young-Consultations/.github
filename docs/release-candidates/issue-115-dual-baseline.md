# Issue #115: dual-baseline release candidate gate record

Status: DRAFT / NOT PUBLISHABLE. This record is a preparatory artifact, not an attestation, immutable adapter release, registry activation, or permission to execute Codex.

## Evidence and candidate identity

- Source issue: https://github.com/Young-Consultations/.github/issues/115
- Root defect: https://github.com/Young-Consultations/consulting-playbook/issues/93 (DEF-0125)
- Implementation: https://github.com/Young-Consultations/consulting-playbook/pull/96
- Merged target baseline: `405981a9ca2ddca0020aa56e77d38e5a1d1b8daa`
- Existing adapter release: `codex-adapter-v3.1.0` -> `4f15841efcba4883770b5e32c0582f733d73eb91`
- Existing control-plane release: `ai-sdlc-v3.1.0` -> `e9d11fc99fee73d247c93699f058ed64786bd4c0`
- Current control-plane main baseline for this draft: `bd0b94dec217bccb4ecd8c3c10650f057ab8d392`
- Candidate target version: `codex-adapter-v3.1.1` (provisional PATCH pending interface and security compatibility validation).
- Candidate control-plane version: `ai-sdlc-v3.1.1` (provisional PATCH pending compatibility validation).
- Existing registry remains pinned to `codex-adapter-v3.1.0`. No candidate tag or report digest is asserted.

## Pre-publication release gates (all pending unless explicitly evidenced)

- [ ] Finish interface and security compatibility review. Preliminary compare confirms 61 commits after v3.1.0 and new protected executor authorization, content checkout, sandbox and publication safeguards; PATCH 3.1.1 remains provisional pending compatibility decision.
- [ ] Verify complete exact-commit conformance and effect traps. GitHub post-merge run 39612598899 succeeded at `405981a9ca2ddca0020aa56e77d38e5a1d1b8daa`; run success is not an independently reproduced complete release verification.
- [x] Confirm committed canonical v2 conformance pin exists at `consulting-playbook/config/mvp-conformance-pin.json`, including exact shared and target blob identities.
- [ ] Independently verify those blobs at the proposed immutable release SHA and calculate committed report SHA-256; do not embed the report-containing commit SHA in the report.
- [ ] Verify the target workflow's protected `CODEX_AUTHORIZED_CONTROL_PLANE_SHA` policy and immutable `github.workflow_ref` / `github.workflow_sha` binding against the prospective registry; do not set a production variable from this draft.
- [ ] Only after evidence passes, publish the new immutable adapter tag and independently resolve its exact SHA.
- [ ] In a follow-up change to this draft PR, update `config/codex-repositories.json` with the real adapter tag, SHA and report digest, plus the coherent candidate manifest, runtime record, receiver references and release documentation. No placeholder identity is acceptable in a publishable registry.
- [ ] Run `python scripts/validate_release.py`, `--require-candidate-ready`, complete tests, registry/YAML/actionlint, `git diff --check`, each affected `verify_release_target_workflows.py --repository`, and no-effect router smoke verification.
- [ ] Obtain required protected checks and either Copilot or Codex review; address all comments. Copilot review on PR #116 returned quota-exhausted (not a completed review); obtain completed Codex review or restore Copilot review capacity.
- [ ] Merge reviewed control-plane candidate; publish immutable control-plane tag at exact merge SHA; separately review and merge publication attestation.
- [ ] Separately migrate source consumers, verify deployed runtime preflight and authorize fresh-identity REAL acceptance. No replay of finalized portfolio-tasks #167.
- [ ] After acceptance, reconcile DEF-0125 ledger, engineering journal, authoritative requirements/architecture/interface documentation, and affected AI_CONTEXT.md only after decisions are resolved.

## Explicit holds

Do not dispatch REAL or paid Codex, alter protected settings/secrets, move tags, change active registry pins, or assert production readiness from green CI alone. This PR may remain draft until the adapter tag and its verified report are available.

## Initial GitHub verification (2026-10-22)

- Compare: https://github.com/Young-Consultations/consulting-playbook/compare/codex-adapter-v3.1.0...405981a9ca2ddca0020aa56e77d38e5a1d1b8daa (61 commits ahead; detailed changes require security/compatibility assessment).
- Exact merged SHA workflow: https://github.com/Young-Consultations/consulting-playbook/actions/runs/39612598899 (completed/success, head SHA `405981a9ca2ddca0020aa56e77d38e5a1d1b8daa`).
- Current conformance pin: https://github.com/Young-Consultations/consulting-playbook/blob/405981a9ca2ddca0020aa56e77d38e5a1d1b8daa/config/mvp-conformance-pin.json (`pin_format_version: 2`).
- Current conformance report: https://github.com/Young-Consultations/consulting-playbook/blob/405981a9ca2ddca0020aa56e77d38e5a1d1b8daa/.ai-sdlc/conformance/tc-mvp-ci-001.json (29 passing scenario entries; zero prohibited real effects; `adapter_tag_published: false`).
- Copilot review quota notice: https://github.com/Young-Consultations/.github/pull/116; cannot count as a completed reviewer approval.
- No adapter tag was published and no active registry, manifest, or environment authorization changed in this increment.

## Gate 1–4 evidence verification, 2026-10-23

**Candidate identity (PASS):** consulting-playbook exact commit `405981a9ca2ddca0020aa56e77d38e5a1d1b8daa` confirmed from GitHub commit tree. GitHub Actions run [39612598899](https://github.com/Young-Consultations/consulting-playbook/actions/runs/39612598899) has the same head SHA and a successful `offline-conformance` job, including repository checks, exact shared oracle and no-effect evidence steps.

**Pinned target blobs (PASS):** fetched `config/mvp-conformance-pin.json` at exact commit and recursively resolved its Git tree: 17/17 target-file blob SHAs match, no discrepancies. Pin format is v2, adapter revision and compatibility SHA match the committed conformance report.

**Conformance evidence (PASS as recorded in exact-SHA CI):** committed `.ai-sdlc/conformance/tc-mvp-ci-001.json` has 29 passing scenario entries, no failures, and zero in all ten prohibited-effect counters. Report blob SHA `13e3e4edc8492ca442b4d77f92f5dae44fd753dc`. Report still declares `adapter_tag_published: false` and does not establish production readiness.

**Compatibility (PENDING final decision):** compared candidate with immutable `codex-adapter-v3.1.0`; changes include new protected `CODEX_AUTHORIZED_CONTROL_PLANE_SHA` binding and fail-closed workflow SHA authorization, separate current-content checkout, candidate sandbox, and publication race safeguards. No `contracts/` schema paths appear among changed files. A reviewer must resolve whether the protected variable introduces a new required operational contract and whether PATCH is the correct SemVer level. The existing workflow still references `ai-sdlc-v3.1.0` receiver/preflight; new release coordination and controlled environment binding must be verified before deployment.

**Outstanding evidence:** independently compute the exact committed report's SHA-256 from downloaded exact bytes and confirm the shared compatibility-file blobs against the referenced control-plane commit; complete interface/security compatibility decision. The supplied local ZIP snapshot is older than this candidate, so local tests from that ZIP are not accepted as exact-candidate evidence. No tag, registry, protected variable, or REAL execution has been changed.


## Independent release preparation, 2026-10-28

### Verified evidence

- Exact target candidate remains `405981a9ca2ddca0020aa56e77d38e5a1d1b8daa` (tree `cd04fe7541bc40773d42e859905f5a3bd5d4f054`). All 17 target pin entries independently match GitHub's recursive commit tree.
- All six shared schema/fixture blob identities independently match organization commit `e27b8a541afbd27b4be5606a19ffa43637ad312a`.
- Downloaded the committed report using base64 encoding to preserve exact bytes. Blob `13e3e4edc8492ca442b4d77f92f5dae44fd753dc` has SHA-256 **`53368781f7bd02ce1831119f1e057e48d8ae4224a6f4f1a2a2ceca1205c29a7f`**. All 29 scenarios pass and all ten prohibited-effect counters are zero. The locally available reviewed tree produces the same digest. This resolves the outstanding digest/shared-file verification above.
- Corrected the escaped newline reported in Codex discussion r4352524117 so the independent verification gate renders as a separate checkbox.

### Compatibility recommendation for owner review

The provisional target PATCH classification is not established. The new protected environment variable `CODEX_AUTHORIZED_CONTROL_PLANE_SHA` is mandatory: a previously configured 3.1.0 environment cannot run the new adapter until it has an independently authorized registry snapshot. Historical drafts without complete immutable provenance also cease to be reusable. These change accepted operational prerequisites and observable reuse policy. Under `docs/releases.md`, PATCH requires no interface or observable policy change. Recommend **MAJOR target adapter `codex-adapter-v4.0.0`**, subject to owner release approval; unchanged JSON schemas alone do not establish PATCH compatibility. No version is reserved or published by this recommendation.

Control-plane version classification must be assessed separately against its final diff. A registry-only compatible implementation correction may qualify for PATCH; adding required receiver inputs/permissions or altering existing registry semantics requires the corresponding higher level. Do not infer the control-plane major from the target's version number.

### Concrete next implementation sequence

1. Approve the target version classification and whether the target retains its existing immutable 3.1.0 receiver/preflight binding or migrates to the next organization release. The current target pins both to 3.1.0. Verify receiver acceptance of the proposed admission release; a new organization admission tag is not automatically accepted by the old receiver. If migration is needed, make a separate target change and regenerate the pin, report, digest, CI and review before selecting its release commit.
2. Validate the chosen target against a proposed immutable registry binding in no-cost fixtures, including correct/missing/wrong workflow SHA/ref and missing/wrong authorized control-plane SHA. Configure policy only after the final registry-bearing commit exists. The environment's authorized SHA must name that independently reviewed snapshot, avoiding any candidate's attempt to record its own future commit.
3. After explicit release approval, publish the new target tag at the approved tested commit. Populate this PR's registry entry with its resolved SHA and committed report digest, then coordinate manifest/package/runtime/receiver policy and source consumer migration as required by the chosen organization release. Use the release-aware verifier for the temporary unpublished-receiver window described in `docs/releases.md`.
4. Complete candidate readiness, every registered target verification, no-effect SIM, current-commit CI and Codex or Copilot review before release-candidate merge. Follow with organization tag publication and the separate publication-attestation PR, then environment binding/source migration/deployed preflight and a separately approved fresh REAL identity.

Issue #115 currently authorizes planning and no-cost verification only and explicitly excludes tag publication, registry/manifest activation, environment changes and REAL execution. This record advances that authorized preparation and presents concrete release decisions for approval. DEF-0125 remains investigating; finalized source #167 is not a reusable acceptance identity.


## Owner approval and migration candidate, 2026-10-28

The owner approved the preceding release classification/migration proposal. Proceed with major target `codex-adapter-v4.0.0` and coordinate the atomic organization release as `ai-sdlc-v4.0.0`; retain v2 payload schemas. Target migration PR: https://github.com/Young-Consultations/consulting-playbook/pull/97 at `8a0b3087229eb0da784a04d2bdaa9f47aaa7a072`. It pins both receiver and credential preflight to 4.0.0 and regenerates its pin/report. The earlier 405981a report digest remains historical evidence, not the digest for this new candidate. CI/review and release-aware receiver verification are required before target tagging. Approval covers release preparation/publication after those gates; environment changes and fresh REAL acceptance retain their separate operational gates.
