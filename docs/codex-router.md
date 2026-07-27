# Organization Codex router

The organization router is a policy boundary between canonical planning output and repository execution. Portfolio intake supplies one JSON `task_payload` conforming to `task-contract.schema.json`; the router never interprets repository-specific fields.

## Canonical route

The reusable `.github/workflows/codex-router.yml` accepts only `task_payload` plus the narrowly scoped dispatch secret. The router:

1. validates `ai-sdlc-contract/v1`, approval status, the `codex` executor, and an empty dependency list;
2. authorizes the target and task type against `config/codex-repositories.json`;
3. constructs and schema-validates one execution input;
4. dispatches the registered workflow with exactly these standard inputs: `contract_version`, `correlation_id`, `source_issue`, `target_repository`, `task_type`, `priority`, `executor`, `parallel_safe`, `draft_pr_only`, `instructions`, `requested_branch`, and `timeout_minutes`.

`task_id` becomes the unchanged execution `correlation_id`. The requested branch is deterministically derived from it, so retrying the same attempt cannot request multiple draft-PR branches. Draft-only execution is mandatory; this workflow cannot merge.

Rejected routes return a deterministic JSON result and one of: `contract-validation`, `authorization`, `dependency`, `repository-routing`, `publication`, or `unknown`.

## Concurrency

Concurrency keys incorporate the normalized target repository, source issue, parallel-safety mode, and a policy boundary. Parallel-safe work uses the correlation ID boundary. Non-parallel-safe work uses the task project/component boundary. Duplicate payloads therefore receive the same group and branch, while explicitly parallel-safe attempts may proceed independently.

## Caller

```yaml
jobs:
  route:
    uses: Young-Consultations/.github/.github/workflows/codex-router.yml@main
    permissions:
      contents: read
      actions: read
    with:
      task_payload: ${{ needs.portfolio-task.outputs.canonical_task_payload }}
    secrets:
      CODEX_ROUTER_TOKEN: ${{ secrets.CODEX_ROUTER_TOKEN }}
```

The token should be a repository-scoped token or GitHub App installation token able to dispatch only registered target workflows.

## Registry changes

Every registration contains only shared policy keys: `enabled`, `workflow_ref`, `allowed_task_types`, `codex_environment`, `max_parallel_tasks`, `draft_pr_only`, and `contract_version`. Run `python3 scripts/codex_router.py validate-registry` in CI whenever registry or router policy changes. Repository differences belong only in this registry; aliases and target-specific parsing are prohibited.
