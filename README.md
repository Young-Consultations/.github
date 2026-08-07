# .github

See the [Young Consultations AI-SDLC vision](docs/VISION.md) for the
authoritative organization and control-plane intent and boundaries.
Read the [requirements baseline](docs/requirements/README.md) and then the
[proposed software architecture](docs/architecture/README.md) before changing
control-plane behavior. The architecture remains non-authoritative until the
requirements baseline and architecture receive their required approvals.

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
deployed canonical contract directory. Legacy normalization is intentionally
limited to safe spellings such as `P1`, `Codex`, and `Draft PR`; task-type
migrations require an explicit mapping through `normalize_payload`.

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
separate execution-level test. The organization repository has no
`codex-execute.yml`: the organization router is its only dispatch boundary,
and execution workflows are owned by registered target repositories.

The reusable router defaults to canonical `execution_mode: implement` for
production calls. The smoke workflow explicitly sends `execution_mode: verify`,
which tells a conforming target to finish after authorization and read-only
validation. A successful verification intentionally invokes no Codex runtime,
does not require repository changes, and creates neither a branch nor a pull
request.

## Platform and execution ownership

`Young-Consultations/.github` is the organization AI-SDLC platform repository.
It owns the canonical schemas, shared Python validator, repository registry,
organization router, and contract tests. It validates and routes work but does
not execute repository changes.

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
