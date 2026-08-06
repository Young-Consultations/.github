# Error Handling Strategy

## Error taxonomy

| Category | Examples | Retry expectation | Owner / recovery |
| --- | --- | --- | --- |
| Contract validation | Malformed, unknown field/version, invariant conflict | No; correct producer/version | Producer + contract owner |
| Authentication/authorization | Unknown caller, absent/stale approval, disallowed scope | No automatic retry | Planning/security owner re-establishes authority |
| Registration/policy | Unknown/disabled target, zero/multiple match, invalid snapshot | No until reviewed policy change | Control-plane owner |
| Compatibility | Unsupported version/mode/interface/permission | No until adoption/remediation | Control-plane + target owners |
| Dependency transient | Platform outage, rate limit, temporary endpoint failure | Bounded backoff/jitter with same identity/payload | Operations; respect retry hints/budget |
| Delivery uncertainty | Timeout/lost acknowledgement | Reconcile first; then unchanged retry only | Control-plane operator |
| Idempotency ambiguity | Conflicting ownership marker/effects/immutable fields | Never automatically | Isolate and target owner reconciles |
| Target execution | Validation/test/agent/publication failure | Per canonical retryability; no scope mutation | Target owner |
| Evidence integrity | Missing, mismatched, inaccessible, contradictory result | No new effect; quarantine/reconcile | Target + security/operations |
| Internal defect | Unhandled invariant/serialization/policy error | Fail closed; incident and rollback | Control-plane owner |
| Cancellation | Authorized cancellation/platform cancellation | Do not infer rollback of effects | Lifecycle owner reconciles |

## Error contract

Every exposed failure contains a stable machine code/category, sanitized human summary, identities that were safely established, phase, side-effect certainty (`none`, `possible`, `known`), retryability and prerequisite, responsible owner, safe next action, and evidence reference. Stack traces, tokens, authorization headers, raw sensitive payloads and internal URLs are not public diagnostics.

## Propagation and fault isolation

Adapters translate infrastructure errors once into domain failure classifications. Application services return typed decisions. Boundary callers receive canonical failure/result forms; no component reports success merely because a lower-level call returned without error. Circuit breaking/rate limiting may isolate one dependency or target, while unrelated targets continue. Validation and policy failures occur before dispatch credentials are used.

## Recovery rules

Preserve delivery identity and immutable payload; cap retries and elapsed time; honor external retry guidance; record every attempt; reconcile uncertain effects before retry; requery after creation races; and require humans for conflicting evidence or policy. Rollback selects known-good immutable releases and does not erase audit evidence.
