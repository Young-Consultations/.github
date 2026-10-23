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
- [x] Confirm committed canonical v2 conformance pin exists at `consulting-playbook/config/mvp-conformance-pin.json`, including exact shared and target blob identities.\n- [ ] Independently verify those blobs at the proposed immutable release SHA and calculate committed report SHA-256; do not embed the report-containing commit SHA in the report.
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
