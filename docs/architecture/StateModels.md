# State Models

## Delivery lifecycle

```mermaid
stateDiagram-v2
  [*] --> Received
  Received --> Rejected: validation/approval fails
  Received --> Admitted: all admission conditions pass
  Admitted --> Rejected: zero/multiple/incompatible route
  Admitted --> Routed: exactly one route
  Routed --> Dispatching
  Dispatching --> AwaitingResult: acknowledged
  Dispatching --> Uncertain: timeout/lost acknowledgement
  Uncertain --> AwaitingResult: reconciliation or safe unchanged retry
  Uncertain --> Failed: nonrecoverable/expired
  AwaitingResult --> InProgress: valid progress
  InProgress --> InProgress: later valid progress
  AwaitingResult --> Terminal
  InProgress --> Terminal
  Terminal --> [*]
  Rejected --> [*]
  Failed --> [*]
```

Terminal outcome variants include `succeeded`, `verified`, `duplicate-reused`, `ambiguous-rejected`, `cancelled`, `rejected`, and `failed` as supported by the active contract. Entry requires a schema-valid, identity-consistent result and required evidence. Terminal states cannot regress. Unknown/absent evidence remains awaiting, uncertain, or failed—not successful.

## Registration lifecycle

```mermaid
stateDiagram-v2
  [*] --> Proposed
  Proposed --> Disabled: policy record valid
  Disabled --> Verification: owner/security approval requested
  Verification --> Disabled: compatibility failure
  Verification --> Enabled: all gates and human approval pass
  Enabled --> Isolated: incident, drift, incompatibility, or risk
  Isolated --> Verification: remediation complete
  Enabled --> Deprecated: planned offboarding
  Deprecated --> Disabled: dispatch stopped
  Disabled --> Retired: retention/offboarding complete
  Retired --> [*]
```

Only `Enabled` is routable. Isolation affects one target without preventing unrelated target routing.

## Compatibility release lifecycle

```mermaid
stateDiagram-v2
  [*] --> Draft
  Draft --> Candidate: artifacts complete
  Candidate --> Draft: verification fails
  Candidate --> Published: checks + governed approval
  Published --> Supported
  Supported --> Deprecated: notice/migration approved
  Deprecated --> Retired: support window ends
  Supported --> RolledBack: unacceptable risk/failure
  Published --> RolledBack
```

Published identity and contents are immutable. Rollback selects a recorded known-good identity; it never mutates the failed release.

## Approval/admission lifecycle

An authored task becomes `Approved` only through authoritative human action. It may become `Stale` after material task/policy change or `Withdrawn` by authority. Admission requires `Approved` and fresh provenance at the decision point. A prior admission does not silently authorize changed work.

## Work lifecycle

```mermaid
stateDiagram-v2
  [*] --> proposed
  proposed --> approved: human approves current task ID
  approved --> queued: admitted for controlled routing
  approved --> withdrawn: approval revoked
  proposed --> superseded: material replacement
  approved --> superseded: approved revision changes
  queued --> executing: target accepts
  queued --> withdrawn: revoked before target starts
  queued --> cancelled: human cancels before start
  executing --> completed: validated terminal result
  executing --> failed: rejection/execution/validation failure
  executing --> cancelled: best-effort stop; no new effects
  completed --> [*]
  failed --> [*]
  withdrawn --> [*]
  cancelled --> [*]
  superseded --> proposed: replacement revision
```

`proposed` has no execution authority. `approved` is the only v2 task state accepted for admission and binds the task
identity to one target. `queued` is a post-admission source projection, not a
router authorization; it cannot be replayed through the v2 boundary. A material
edit receives a new task ID and fresh approval.
`executing` means the target accepted the delivery, not that it succeeded.
`completed` requires a valid success/verified/duplicate-reused result and, for
implement mode, validation evidence plus one managed draft PR. `failed` is a
terminal unsuccessful outcome. `withdrawn` revokes approval before execution;
`cancelled` is a human stop request/terminal disposition whose in-flight
interruption may be best-effort; `superseded` means a different revision needs
new approval. Terminal evidence is retained and never rewritten as success.
