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

The 2.3.1 recovery candidate adds a separate publishability gate:

```console
python scripts/validate_release.py --require-publishable
```

It intentionally fails until every target is bound to an immutable
`codex-adapter-v*` tag/commit with a digest-verified complete adapter report and
the receiver has a reviewed non-empty journal-author policy. The default live
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
work but does not execute repository changes. All targets remain
disabled until their owners approve immutable adapter revisions and publish the
required conformance evidence.

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
targets supply only the result-delivery credential. It never uses the
caller-associated reusable-workflow context to select policy content.
The current empty list is deny-all, not a permissive default. All targets remain
disabled pending owner conformance and deployment evidence. See the
[next-MVP path audit](docs/next-mvp-path-audit.md).
