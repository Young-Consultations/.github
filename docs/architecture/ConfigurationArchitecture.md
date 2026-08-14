# Configuration Architecture

## Configuration domains

| Domain | Examples | Owner |
| --- | --- | --- |
| Contract/release | Supported majors, artifact identities/digests, release and rollback identity | Contract/release authority |
| Target capabilities | Target identity/owner, endpoint, versions/modes/types, concurrency, draft policy, security environment, idempotency capabilities | Control-plane registry owner with target/security review |
| Activation | Current enabled/disabled boolean for every capability entry | Control-plane owner with target/security approval; router is sole enforcer |
| Result journal trust | Exact GitHub App/bot authors permitted to establish admission, receipt, and forwarding markers | Control-plane security/release owner; immutable compatibility configuration |
| Runtime request | Canonical task and explicit execution mode | Planning caller; validated by control plane |
| Operational policy | Timeouts, retry budgets, SLO/alert thresholds, retention/classification | Operations/security governance |
| Credentials | Dispatch/read-only identities and secret references | Security/platform owner |

## Precedence

Normative contract and security invariants cannot be overridden. For configurable behavior, precedence is: immutable release policy → reviewed registry entry → explicit validated request where the policy permits choice → documented safe default. Environment/runtime values may select an already approved resource or operational tuning but cannot enable targets, broaden scope, change mode semantics, accept incompatible versions, permit non-draft publication, or weaken validation.

## Validation and activation

Validate syntax, schema, uniqueness, referential integrity, version coherence,
target/workflow identity, owner, exact dispatch inputs, receiver compatibility,
modes/types, positive limits, publication/idempotency/security policy,
digest-bound shared-oracle evidence, a non-recursive exact-file conformance pin,
separate immutable tag-to-commit/report-digest bindings, and secret-reference form before
activation. Unknown keys fail closed. A decision reads one version-identified
immutable snapshot; mid-run changes apply only to later decisions. Sensitive
values are supplied through protected secret references, never committed
configuration. Journal-author login names are policy identities, not secrets;
their allowlist is reviewed and released here rather than supplied by a target.

## Defaults

Defaults must be explicit, documented, safe, test-covered and versioned.
Security-sensitive absence means disabled/rejected, not permissive behavior.
An empty journal-author allowlist denies every result, and missing target
conformance produces not-evaluated/failure rather than PASS. Mode should be
explicit at the canonical request even if a convenience interface offers a
documented production default; the constructed execution input never relies on
inference.

## Change management

Configuration changes receive requirement/risk/security/compatibility review, deterministic validation, target compatibility where relevant, audit identity, staged enablement, and rollback. Production endpoints use immutable references. Emergency isolation may disable a target immediately under documented authority but cannot silently delete evidence.

## Unknown policy values

Approval freshness, trusted journal-author deployment identities, retention
periods, retry/time budgets, signing rules, SLO alert windows and credential
implementation require organization decisions. Architecture defines their
required properties and a deny-all missing-value state, not invented values.
