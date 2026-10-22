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

- [ ] Independently compare merged target to v3.1.0 for workflow inputs/outputs/secrets/permissions, receiver, payload, sandbox and content-baseline behavior. Record SemVer decision.
- [ ] Verify exact merged target tree and all 29 shared oracle scenarios, including zero prohibited real effects, on the intended release commit.
- [ ] Produce canonical v2 conformance pin with exact adapter/harness/shared-file blob identities and independently calculate committed report SHA-256. Do not embed the report-containing commit SHA in the report.
- [ ] Verify the target workflow's protected `CODEX_AUTHORIZED_CONTROL_PLANE_SHA` policy and immutable `github.workflow_ref` / `github.workflow_sha` binding against the prospective registry; do not set a production variable from this draft.
- [ ] Only after evidence passes, publish the new immutable adapter tag and independently resolve its exact SHA.
- [ ] In a follow-up change to this draft PR, update `config/codex-repositories.json` with the real adapter tag, SHA and report digest, plus the coherent candidate manifest, runtime record, receiver references and release documentation. No placeholder identity is acceptable in a publishable registry.
- [ ] Run `python scripts/validate_release.py`, `--require-candidate-ready`, complete tests, registry/YAML/actionlint, `git diff --check`, each affected `verify_release_target_workflows.py --repository`, and no-effect router smoke verification.
- [ ] Obtain required protected checks and either Copilot or Codex review; address all comments.
- [ ] Merge reviewed control-plane candidate; publish immutable control-plane tag at exact merge SHA; separately review and merge publication attestation.
- [ ] Separately migrate source consumers, verify deployed runtime preflight and authorize fresh-identity REAL acceptance. No replay of finalized portfolio-tasks #167.
- [ ] After acceptance, reconcile DEF-0125 ledger, engineering journal, authoritative requirements/architecture/interface documentation, and affected AI_CONTEXT.md only after decisions are resolved.

## Explicit holds

Do not dispatch REAL or paid Codex, alter protected settings/secrets, move tags, change active registry pins, or assert production readiness from green CI alone. This PR may remain draft until the adapter tag and its verified report are available.
