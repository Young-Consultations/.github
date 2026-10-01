# .github

See the [Young Consultations AI-SDLC vision](docs/VISION.md) for the
authoritative organization and control-plane intent and boundaries.
Read the [approved requirements baseline](docs/requirements/README.md) and then
the [next-MVP software architecture](docs/architecture/README.md) before
changing control-plane behavior.

The router, reusable interface, schemas, target-capability registry, and Python
package are released as one immutable compatibility unit. Current activation in
`config/codex-activation.json` is mutable control-plane state and is not part of
that consumer compatibility unit. See [release, upgrade,
deprecation, and rollback procedures](docs/releases.md).

The published [`ai-sdlc-v3.0.3` release](docs/releases/3.0.3.md) is the
current control-plane compatibility baseline at reviewed PR #104 merge commit
`f3229bfa4a06da963cae7c390c6075b4f6c12f7b`. Portfolio-tasks now consumes published 3.0.3 through merged PR #163 at `580eaf3cd88774014d645d3c3ca3718b39b38ce0`.

The matching immutable target is `codex-adapter-v3.0.3` at
`f11852c7f563df16ea4afa9ab75bf766242e7327`. The target conformance adapter
revision is
`sha256:3932def5d016b7db11869a0520087aeedcd092799e61dc8617be8bb2f020be3f`
with report SHA-256
`a739cd3dde3c05121fbfc5360495880e265b76448b504936b8583b5efa972ec8`.

3.0.3 preserves exactly one trusted durable admission for an unchanged logical
delivery across a compatible release retry. Exact same-release admission reuse
remains unconditional; predecessor reuse is allowed only by immutable
target-bound policy, and target compatibility proves that policy is a subset of
the pinned receiver's compatibility allowlist. Ambiguous, malformed,
conflicting, concurrent, or unsupported admission state fails closed before
target dispatch.

Post-publication acceptance is complete. Deployed 3.0.3 Runtime Preflight
36867504568 and immutable REAL readiness preflight 36867939797 passed before
portfolio source adoption. Fresh #159 then produced one corrected terminal
projection through target run 36911342397 and source run 36911478182; unchanged
redelivery through source run 36913373900 and target run 36913463403 returned
`duplicate-reused` for the same delivery/branch/PR #82 before Codex with no
second receiver/source visible effect.

## AI-SDLC contract validation

This repository publishes `ai-sdlc-contracts`, a small Python library backed
directly by the canonical schemas in [`contracts/`](contracts/). Install it in
CI with `python -m pip install .`, then validate mappings without network calls:

```python
from ai_sdlc_contracts import validate_task

validate_task(payload)
```

The equivalent CLI commands are:

```console
python -m ai_sdlc_contracts validate-task payload.json
python -m ai_sdlc_contracts validate-input payload.json
python -m ai_sdlc_contracts validate-result payload.json
```

Set `AI_SDLC_CONTRACT_DIR` only when an installation needs to use a separately
deployed canonical contract directory. Validation is exact: callers must supply
the closed v2 vocabulary, and the package does not normalize aliases or build
source tasks.

## Verification sequence

The deterministic organization conformance oracle is pinned in
`config/mvp-conformance-pin.json` to
`Young-Consultations/.github@e27b8a541afbd27b4be5606a19ffa43637ad312a`.
It verifies the exact shared schema/fixture identities and a non-recursive digest
of the target workflow, adapter, and harness before running every
`TC-MVP-CI-001` scenario through the real `.github` adapter seam. Deterministic
effect adapters trap Codex, branch, commit, push, pull-request, merge, release,
deployment, production, and secret-output effects and write a versioned JSON
report. The report is target conformance evidence only: it does not contain its
own commit SHA, claim production readiness, request activation, create a tag, or
change mutable activation state. The registry separately binds an eventual
immutable adapter tag to its reviewed commit and the report digest.
Static wrapper checks prove only the exact dispatch and receiver interfaces;
idempotency is accepted only from the executable report against the pinned
adapter. Source comments and keyword presence are not behavioral evidence.

```console
python scripts/run_tc_mvp_ci_001.py --report .ai-sdlc/conformance/tc-mvp-ci-001.json
```

[`AI-SDLC Contract Tests`](.github/workflows/ai-sdlc-contract-tests.yml) is the
canonical, read-only verification gate for shared schemas and examples, the
Python validation library, organization router behavior, registry contracts,
integration boundaries, and static contract security checks. It replaces the
workflow formerly displayed as `Router contract tests`; because the display
name and filename changed, branch protection must be updated after merge to
require the new `AI-SDLC Contract Tests` job checks.

The 2.3.2 recovery release retains the separate publishability gate:

```console
python scripts/validate_release.py --require-publishable
```

It fails unless every target is bound to an immutable `codex-adapter-v*`
tag/commit with a digest-verified complete adapter report and the receiver has
a reviewed non-empty journal-author policy. The default live
target verifier reports disabled targets as `not-evaluated` and exits nonzero;
disabled or skipped work cannot create a false organization-wide PASS.

Production-path verification proceeds in this order:

1. **AI-SDLC Contract Tests**
2. **Router smoke test**
3. Registered target-repository execution
4. Full ChatGPT-to-draft-PR end-to-end tests

The contract workflow performs no dispatch, Codex execution, issue mutation,
branch creation, or pull-request publication. The router smoke test remains a
separate execution-level test. The organization control plane does not execute
target changes. Its separately authorized `codex-execute.yml` target adapter is
implemented and has a deterministic no-real-effects conformance candidate, but
it remains disabled and untagged pending review. Its target-only credentials
must remain isolated from router and receiver credentials.

The reusable router defaults to canonical `execution_mode: implement` for
production calls. The smoke workflow explicitly sends `execution_mode: verify`,
which tells a conforming target to finish after authorization and read-only
validation. A successful verification intentionally invokes no Codex runtime,
does not require repository changes, and creates neither a branch nor a pull
request.

## Platform and execution ownership

`Young-Consultations/.github` is the organization AI-SDLC platform repository.
It owns the canonical schemas, shared Python validator, immutable
target-capability registry, mutable target activation state, organization
router, result-receiver boundary, and contract tests. It validates and routes
work but does not execute repository changes. `consulting-playbook` is the sole
enabled target after approval of its immutable passing adapter evidence and
target-compatibility result. `.github`, `portfolio-tasks`, and `slugger` remain
disabled pending separate enablement decisions.

The four registered target repositories—`.github`, `portfolio-tasks`,
`consulting-playbook`, and `slugger`—own their `codex-execute.yml` workflows.
Those workflows consume `execution-input/v2`, perform verification or Codex
implementation in the target repository, and emit `execution-result/v2`.
The only target entry point is `workflow_dispatch` with exactly two required
string inputs, `execution_input_json` and `concurrency_group`.

## Delivery guarantee

The control plane uses at-least-once delivery plus target-side idempotency. The
guarantee is exactly-once externally visible publication effects for one
canonical `delivery_id`: at most one managed deterministic branch and one open
managed draft PR. It intentionally does not claim transactional exactly-once
Codex execution.

## Current MVP path

The sole supported organization path is approved `task-contract/v2` admission
through [`codex-router.yml`](.github/workflows/codex-router.yml), target-owned
`execution-input/v2` handling, and canonical `execution-result/v2` return through
[`codex-result-receiver.yml`](.github/workflows/codex-result-receiver.yml). The receiver validates the authenticated caller and canonical result against the
source-owned admission journal, records a digest-only durable receipt, deduplicates
by delivery ID, and forwards one validated `repository_dispatch` projection. It
loads trusted journal-author identities from
[`config/codex-result-trust.json`](config/codex-result-trust.json) through a
self-pinned composite action in the same immutable control-plane release;
the enabled v3 target supplies only the dedicated
`RESULT_WRITER_PRIVATE_KEY`; the receiver mints a fresh short-lived
`ai-sdlc-result-writer` installation token scoped to `portfolio-tasks` and
passes only that token to its immutable action. It never uses the
caller-associated reusable-workflow context to select policy content.
The current reviewed author lists are explicit policy, not permissive defaults.
`consulting-playbook` is the sole enabled target; its registry entry records
immutable passing adapter evidence sufficient for activation, and the
target-compatibility workflow is green. `.github`, `portfolio-tasks`, and
`slugger` remain disabled. See the [next-MVP path
audit](docs/next-mvp-path-audit.md).
