# Default-branch change control

**Status:** Approved implementation guidance for GH-OR-002 and DEF-0056.

## Decision

The fail-closed prevention boundary for direct implementation writes is GitHub's
repository ruleset enforcement, not an AI-agent convention or prompt. Every core
AI-SDLC repository must have at least one **active branch ruleset** targeting
`~DEFAULT_BRANCH` that:

- requires a pull request before the default branch can be updated;
- requires review-thread resolution before merge;
- blocks branch deletion;
- blocks non-fast-forward updates; and
- has no bypass actors.

This narrow control is the authoritative repair for DEF-0056. It prevents an
omitted branch parameter in an implementation write from silently targeting the
default branch. It does not by itself claim full satisfaction of every
GH-OR-002 review/approval requirement.

Normal reviewed pull-request merges remain allowed. Release/tag operations are
not default-branch implementation writes and are governed by their existing
release controls.

## Current scope

The policy applies to:

- `Young-Consultations/.github`
- `Young-Consultations/portfolio-tasks`
- `Young-Consultations/consulting-playbook`
- `Young-Consultations/slugger`

The machine-readable policy is
[`config/default-branch-governance.json`](../config/default-branch-governance.json).

## Required GitHub ruleset

For each repository, configure a branch ruleset with:

- **Enforcement:** Active
- **Target branches:** Include default branch
- **Bypass list:** empty
- **Require a pull request before merging:** enabled
- **Required approvals:** 0 for this single-maintainer MVP control
- **Require conversation resolution before merging:** enabled
- **Restrict deletions:** enabled
- **Block force pushes / non-fast-forward updates:** enabled

Existing status-check rules may remain in the same ruleset or a separate one.
Do not remove stronger controls when adding this guard.

The zero-approval setting is deliberate for this repair: the defect is direct
default-branch mutation, and the sole maintainer cannot self-approve a pull
request. Review quality, code-owner/security approval, and required-check policy
remain governed by their existing requirements and may be tightened separately.

## Verification

Run the offline unit tests:

```console
python -m pytest tests/test_default_branch_governance.py
```

After an administrator applies the live rulesets, run:

```console
python scripts/audit_default_branch_governance.py --json
```

The command reads the live repository rulesets and exits nonzero unless every
repository has one active, no-bypass default-branch ruleset containing the
required rules. API failures also fail closed.

The manual
[`Default Branch Governance Audit`](../.github/workflows/default-branch-governance-audit.yml)
workflow runs the same check and preserves the GitHub Actions run as executable
evidence.

## DEF-0056 closure gate

Do not close DEF-0056 or issue #80 from documentation or unit-test evidence
alone. Closure requires:

1. the live GitHub rulesets to be configured;
2. the live governance audit to pass for all four repositories; and
3. the resulting run/API evidence to be recorded in DEF-0056 and issue #80.

Only after those conditions are satisfied should AI_CONTEXT describe the
default-branch write guard as implemented.
