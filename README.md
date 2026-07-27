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
