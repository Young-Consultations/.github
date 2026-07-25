# Organization Codex router

This repository owns the reusable organization-level Codex routing policy. Portfolio intake and approval remain in `portfolio-tasks`; implementation workflows remain in registered target repositories such as `slugger`, `consulting-playbook`, and `portfolio-tasks` itself.

## Router contract

Use `.github/workflows/codex-router.yml` with `workflow_call`. The caller must provide typed inputs for the source issue, target repository, task type, project/component, priority, parallel-safety, dependency status, and approved execution metadata. The router validates those inputs against `config/codex-repositories.json`, rejects unknown or disabled repositories before execution, and dispatches the target repository workflow with `draft_pr_only=true`.

The router output shape is normalized:

- `execution_result`
- `target_repository`
- `generated_branch`
- `draft_pr_url`
- `validation_result`
- `test_result`
- `diagnostic_summary`

The router never merges pull requests. Target repositories must create draft PRs that require human review and merge.

## Registered production targets

`Young-Consultations/portfolio-tasks` is registered for the narrow task types `automation`, `backlog-governance`, `ci-cd`, `documentation`, and `repository-maintenance`. Approved work is dispatched to `Young-Consultations/portfolio-tasks/.github/workflows/codex-execute.yml@main` with the `portfolio-tasks-codex-production` environment identifier. The registration remains subject to dependency validation, approved execution metadata, component concurrency, the repository allowlist, and the draft-PR-only boundary.

## Caller pattern

```yaml
name: Route approved Codex task

on:
  workflow_dispatch:
    inputs:
      source_issue:
        required: true
        type: string
      target_repository:
        required: true
        type: string
      task_type:
        required: true
        type: string
      project_component:
        required: true
        type: string

permissions:
  contents: read
  actions: read

jobs:
  route:
    uses: Young-Consultations/.github/.github/workflows/codex-router.yml@main
    permissions:
      contents: read
      actions: read
    with:
      source_issue: ${{ inputs.source_issue }}
      target_repository: ${{ inputs.target_repository }}
      task_type: ${{ inputs.task_type }}
      project_component: ${{ inputs.project_component }}
      priority: normal
      parallel_safe: false
      dependency_status: satisfied
      approved_execution_metadata: ${{ vars.APPROVED_CODEX_METADATA_JSON }}
    secrets:
      CODEX_ROUTER_TOKEN: ${{ secrets.CODEX_ROUTER_TOKEN }}
```

## Registering a future repository

1. Add exactly one entry under `repositories` in `config/codex-repositories.json`.
2. Set `enabled: true` only after the target repository owns a draft-PR-only execution workflow.
3. Keep `allowed_task_types` narrow and reviewable.
4. Set a real Codex environment identifier before enabling the repository; production registrations must not use placeholders.
5. Set `max_parallel_tasks` and component concurrency policy based on the repository's write-conflict profile.
6. Add or update contract tests for registered, disabled, unknown, conflicting, and parallel-safe routing behavior.

Do not add demo repositories to the production registry unless they are marked `test_only: true`.

## Manual smoke test

Use a non-production task and a repository-scoped `CODEX_ROUTER_TOKEN`. Trigger the caller workflow with a registered repository, `dependency_status=satisfied`, and metadata similar to:

```json
{"approved": true, "approved_by": "portfolio-tasks", "approval_id": "smoke-test-001"}
```

Confirm the router validates the task, dispatches the target boundary, and returns either a target draft PR URL or a pending target-workflow diagnostic. Do not merge the draft PR during smoke testing.
