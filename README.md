# .github

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
3. **Execute approved Codex task**
4. Full ChatGPT-to-draft-PR end-to-end tests

The contract workflow performs no dispatch, Codex execution, issue mutation,
branch creation, or pull-request publication. The router smoke test remains a
separate execution-level test, and the production router and approved-task
execution workflows remain independent.
