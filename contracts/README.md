# AI-SDLC contracts

This directory is the canonical, implementation-neutral interface for moving a task through the Young-Consultations AI-SDLC. It gives ChatGPT planning, `portfolio-tasks`, the optional `consulting-playbook` or Slugger task source, and Codex one task representation and one execution request/result path. It defines data interchange only: routing, credentials, permissions, and repository-specific behavior remain outside the contracts.

## Ownership

The Young-Consultations `.github` repository owns these schemas. Changes are reviewed and released here before a producer or consumer adopts them. The plain-text [`contract-version.txt`](contract-version.txt) is the authoritative current version; every schema fixes `contract_version` to the same value.

The Python distribution includes byte-for-byte copies of these files under
`ai_sdlc_contracts/contracts`. The validation-library tests compare the two
locations so a release fails before a packaged copy can drift from this
canonical directory. Installed clients load those copies as package resources,
independently of their installation prefix or current working directory.

| Artifact | Purpose |
| --- | --- |
| `task-contract.schema.json` | Planning and approved-task record shared across task sources |
| `execution-input.schema.json` | Request submitted to the single Codex execution path |
| `execution-result.schema.json` | Machine-readable state or terminal outcome from that path |
| `v1/` | Immutable version 1 schemas retained for pinned consumers during migration |
| `examples/` | Complete payloads for producer/consumer fixtures and integration tests |

All objects are closed with `additionalProperties: false`. An unrecognized field therefore fails validation rather than being silently discarded. This is deliberate: there is no v1 compatibility reason to permit extension fields.

## Consumption

Repositories should pin a released schema revision (a commit SHA or release tag), load the relevant JSON Schema, and validate at every trust boundary with a Draft 2020-12 implementation. Producers validate before dispatch; consumers validate again before acting. Format checking must be enabled so URI and date-time formats are enforced. A consumer must reject a payload when validation fails and must not infer, rename, or default required fields.

The intended flow is:

1. Planning creates a task conforming to `task-contract.schema.json`.
2. The approved task is projected into `execution-input.schema.json` without creating an alternate execution path.
3. The required `execution_mode` is `implement` for production work or `verify` for read-only integration verification. It is never inferred from instructions.
4. Implement mode accepts only `executor: codex` and `draft_pr_only: true`, and may publish a draft pull request only. Verify mode must not invoke Codex or create a branch or pull request.
5. The execution system reports progress or a terminal outcome using `execution-result.schema.json`; `verified` intentionally has null branch and pull-request fields.

The schemas neither authorize a repository nor route to it. Repository allowlists and authorization remain policy owned by the executing system. These contracts do not permit automatic merge behavior.

## Versioning and compatibility

Versions use the namespace `ai-sdlc-contract/vN`, where `N` is the major contract version. The version is part of every payload and is matched exactly by each schema.

* **Breaking changes require a new major version.** Removing or renaming a field or enum member, changing its meaning or type, making an optional field required, tightening validation for previously valid data, or changing a required invariant creates `/v2` (or the next major version). Existing versioned schemas remain available while consumers migrate.
* **Backward-compatible additions are limited to optional fields.** An optional field may be added within a major version only after coordinated schema publication. Because objects are closed, consumers must update to the additive schema before producers emit the field. Producers must not send it until all relevant consumers accept it.
* **Enum additions require care.** Consumers commonly treat enums as exhaustive, so a new enum value is considered breaking unless the version's consumer policy explicitly established an unknown-value fallback. Version 1 establishes no such fallback.
* **Version mismatch is a hard failure.** Consumers never coerce an older or newer payload. They select the matching schema or reject it as `contract-validation`.

During a major-version migration, producers may generate old and new payloads at separate boundaries, but a single payload is valid for exactly one version. Changes to examples and automated positive and negative validation tests accompany every contract change.

The root schemas and examples currently publish `ai-sdlc-contract/v2`. Version 2
introduces the required execution mode and the `verified` execution result. The
original closed version 1 schemas remain under [`v1/`](v1/) so existing producers
and consumers can continue validating version 1 payloads while they coordinate
their migration. The router and repository registry migrate together and emit
only version 2 execution payloads.

## Local validation

Install the Python test dependencies and run:

```bash
python -m pytest tests/test_contract_schemas.py
```

The tests use `jsonschema` with format checking, validate all examples, and protect required fields, enums, closed objects, version matching, Codex draft-only execution, repository names, and issue references.

## Delivery identity and idempotency

`execution-input/v2` and `execution-result/v2` include required `delivery_id`.
It is the immutable idempotency key for one logical approved task. Current v2
producers set it to the deterministic task identity (`task_id`); they must not
use workflow run IDs, run attempts, timestamps, or random UUIDs. Rebuilding the
same approved task produces the same value, while materially different logical
work must use a different task identity or be rejected if it attempts to reuse
an existing `delivery_id` with different immutable fields.

`correlation_id` remains an observability field and is not an attempt-specific
identity. Consumers must copy `delivery_id` into every canonical execution
result, including `duplicate-reused` and `ambiguous-rejected` terminal outcomes.
