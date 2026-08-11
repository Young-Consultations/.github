# .github

See the [Young Consultations AI-SDLC vision](docs/VISION.md) for the
authoritative organization and control-plane intent and boundaries.
Read the [approved requirements baseline](docs/requirements/README.md) and then
the [next-MVP software architecture](docs/architecture/README.md) before
changing control-plane behavior.

The router, reusable interface, schemas, registry, and Python package are
released as one immutable compatibility unit. See [release, upgrade,
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

[`AI-SDLC Contract Tests`](.github/workflows/ai-sdlc-contract-tests.yml) is the
canonical, read-only verification gate for shared schemas and examples, the
Python validation library, organization router behavior, registry contracts,
integration boundaries, and static contract security checks. It replaces the
workflow formerly displayed as `Router contract tests`; because the display
name and filename changed, branch protection must be updated after merge to
require the new `AI-SDLC Contract Tests` job checks.

Production-path verification proceeds in this order:

1. **AI-SDLC Contract Tests**
2. **Router smoke test**
3. Registered target-repository execution
4. Full ChatGPT-to-draft-PR end-to-end tests

The contract workflow performs no dispatch, Codex execution, issue mutation,
branch creation, or pull-request publication. The router smoke test remains a
separate execution-level test. The organization control plane does not execute
target changes. Its separately authorized `codex-execute.yml` target adapter is
planned implementation work and must remain isolated from router and receiver
credentials.

The reusable router defaults to canonical `execution_mode: implement` for
production calls. The smoke workflow explicitly sends `execution_mode: verify`,
which tells a conforming target to finish after authorization and read-only
validation. A successful verification intentionally invokes no Codex runtime,
does not require repository changes, and creates neither a branch nor a pull
request.

## Platform and execution ownership

`Young-Consultations/.github` is the organization AI-SDLC platform repository.
It owns the canonical schemas, shared Python validator, repository registry,
organization router, result-receiver boundary, and contract tests. It validates
and routes work but does not execute repository changes. All targets remain
disabled until their owners approve immutable adapter revisions and publish the
required conformance evidence.

The four registered target repositories—`.github`, `portfolio-tasks`,
`consulting-playbook`, and `slugger`—own their `codex-execute.yml` workflows.
Those workflows consume `execution-input/v2`, perform verification or Codex
implementation in the target repository, and emit `execution-result/v2`.

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
by delivery ID, and forwards one validated `repository_dispatch` projection. All
targets remain disabled pending owner conformance and deployment evidence. See the
[next-MVP path audit](docs/next-mvp-path-audit.md).
