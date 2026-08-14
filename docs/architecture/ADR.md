# Architectural Decision Records

These prospective records govern architecture rather than merely describing current code. Open questions require approved follow-up and do not relax the decision.

## ADR-001 — Policy-centric clean architecture

**Context:** Governance semantics must survive workflow/runtime rewrites. **Decision:** Keep domain policy and use cases inward of workflow, transport, storage, schema-engine and telemetry adapters. **Alternatives:** workflow-script-centric logic; shared target library. **Tradeoffs:** more explicit interfaces and mapping, but pure testability and replaceability. **Consequences:** GitHub expressions and API response shapes cannot enter the domain. **Open questions:** packaging/deployment split.

## ADR-002 — One canonical, closed, versioned language

**Context:** Independent repositories otherwise drift into bilateral formats. **Decision:** Define canonical task, execution input and result contracts, validate exact versions at every boundary, and reject unknown fields unless a future contract explicitly defines extension semantics. **Alternatives:** permissive envelopes; consumer inference. **Tradeoffs:** coordinated additions versus predictable meaning. **Consequences:** breaking changes create a major; supported historical artifacts remain immutable. **Open questions:** future extension-envelope policy.

## ADR-003 — Human approval and target-owned execution

**Context:** AI must not acquire approval or production authority. **Decision:** Planning owns approval truth; control plane proves admission/routes; targets implement and publish draft proposals; humans review/merge. **Alternatives:** central executor; automation approval/merge. **Tradeoffs:** more cross-boundary evidence but strong accountability and repository autonomy. **Consequences:** control plane never modifies target code. Approval provenance/freshness is resolved by ADR-009.

## ADR-004 — At-least-once delivery with idempotent visible effects

**Context:** Cross-repository workflow delivery is not transactional. **Decision:** Preserve deterministic delivery identity and immutable payload across retries; targets preflight and create at most one managed branch and open draft PR, requerying after races. **Alternatives:** claim exactly-once transport; control-plane dedupe alone; random attempt identity. **Tradeoffs:** target complexity in exchange for recoverability. **Consequences:** duplicate reuse is canonical; ambiguity fails closed. Result reconciliation transport is resolved by ADR-010.

## ADR-005 — Explicit verify and implement modes

**Context:** Inferred authority can cause unintended mutation. **Decision:** Every request explicitly carries shared mode semantics: verify is read-only; implement may propose through a draft PR only. **Alternatives:** infer from prose or caller/workflow. **Tradeoffs:** strict caller coordination for a clearer security boundary. **Consequences:** mode-specific result invariants and compatibility tests. **Open questions:** additional future modes require a major compatibility assessment.

## ADR-006 — Registry-based deterministic routing

**Context:** Authorized targets/capabilities must be explicit. **Decision:** Use a reviewed, versioned registration snapshot; route only when exactly one enabled compatible target matches. **Alternatives:** convention discovery; caller-supplied workflow; dynamic broad matching. **Tradeoffs:** administrative onboarding versus predictable least privilege. **Consequences:** invalid registry blocks delivery and one target can be isolated. **Open questions:** registry owner/schema evolution.

## ADR-007 — Atomic immutable compatibility releases

**Context:** Router, schema, validator, registry format and checks are interdependent. **Decision:** Bind them in one immutable release manifest with adoption, deprecation and known-good rollback. **Alternatives:** independently version all artifacts; movable branch references. **Tradeoffs:** coordinated releases versus elimination of mixed-version ambiguity. **Consequences:** production consumers pin identities. **Open questions:** signing/attestation enforcement mechanism.

## ADR-008 — Evidence-based asynchronous outcomes

**Context:** Dispatch acknowledgement is not execution success. **Decision:** Separate attempt acknowledgement from target result; accept success only with validated target evidence. **Alternatives:** synchronous router completion; assume success on dispatch. **Tradeoffs:** reconciliation complexity versus honest status. **Consequences:** pending/uncertain are first-class states. ADR-010 selects the MVP result channel.

## ADR-009 — v2 approval admission precedes queue projection

**Status:** Accepted for the next MVP. **Context:** Repository-specific labels have
been externally observed to disagree, and the closed v2 task contract carries a
status but no approval ID, authority, timestamp, or revision digest. A queued
payload therefore cannot independently prove authorization. **Decision:** The
source emits `status: approved` for admission and assigns a new `task_id` after
any material edit. The v2 router accepts only `approved`; the source may project
`queued` only after admission succeeds and must not replay that projection as a
new authorization. Revocation before admission prevents routing; cancellation
after execution starts is best-effort and forbids new effects. **Alternatives:**
add undeclared fields to v2; accept a queue label as approval; introduce v3 in
this MVP. **Tradeoffs:** v2 cannot transport rich approval provenance, but this
rule is representable and fail-closed without an unimplemented interface.
**Consequences:** richer revision-bound evidence requires a future versioned
contract/router migration. Consumers reject non-approved router input.
**Trace:** GH-FR-005, GH-FR-017; TC-MVP-CI-001.

## ADR-010 — Canonical reusable result receiver and source projection

**Status:** Accepted for the next MVP. **Context:** Dispatch acknowledgement is
not a result, direct target-to-issue writes broaden credentials, and polling or
artifacts alone do not define one accountable return boundary. **Decision:** A
target creates `execution-result/v2` and invokes an organization-owned reusable
result-receiver workflow. The receiver authenticates the caller, validates the
contract and identity bindings, deduplicates by the v2 `delivery_id`,
persists evidence, and idempotently forwards the result to the source owner;
`portfolio-tasks` owns issue projection. On timeout, sender and receiver
reconcile receiver evidence and managed-PR markers before unchanged retry.
Conflicting valid-looking results fail closed as ambiguous. Per ADR-013, the
receiver obtains trusted journal-author policy only from its immutable
control-plane bundle; the target supplies only the result-delivery credential.
**Alternatives:**
direct target issue mutation; source polling every target; workflow artifacts
as the sole channel; dispatch status as success. **Tradeoffs:** one additional
hop and receiver availability in exchange for least privilege, uniform
validation, and replayable evidence. **Consequences:** at-least-once transport,
not exactly-once delivery, is assumed; visible issue and draft-PR effects are
idempotent. **Trace:** GH-FR-008/011/012/018; TC-MVP-CI-001,
TC-MVP-E2E-001.

## ADR-011 — `.github` control-plane and execution-target isolation

**Status:** Accepted for the next MVP. **Context:** `.github` owns organization
admission infrastructure but is also one of exactly four useful MVP targets.
Combining its authorities would allow self-approval or bypass. **Decision:** Treat
the control plane and `.github` target adapter as separate trust boundaries. The
adapter runs only after explicit router selection, uses target-only credentials,
is limited to documentation, CI, repository maintenance, and testing, and ends
at a draft PR plus canonical result. It cannot approve, route, mutate another
repository, use control-plane credentials, merge, release, or deploy.
**Consequences:** both roles may share a repository but not an authority; the
registry remains disabled-first and conformance is required before enablement.
**Trace:** GH-FR-002/008–012/017–018; RI-MVP-02; TC-MVP-CI-001.

## ADR-012 — Dynamic targets use one exact dispatch interface

**Status:** Accepted for the 2.3.1 recovery. **Context:** The router chooses a
target at runtime and invokes it with GitHub workflow dispatch. Three reviewed
targets exposed only `workflow_call`, while the compatibility verifier expected
obsolete artifact and run-ID inputs. A green local check therefore did not prove
that the router could invoke the registered endpoint. **Decision:** Every
registered target entry point is `workflow_dispatch` and declares exactly two
required string inputs: `execution_input_json` and `concurrency_group`. The first
contains the complete closed canonical input; the second must equal its canonical
concurrency value. No artifact, run-ID, field-by-field, optional fallback, or
`workflow_call` target interface is active. **Alternatives:** statically select a
reusable workflow; retain multiple transports; accept optional artifact lookup.
**Tradeoffs:** target adapters expose a small transport wrapper, while the router
retains deterministic dynamic selection and one testable interface.
**Consequences:** compatibility verification rejects missing, extra, optional,
wrongly typed, untagged, or undispatchable target interfaces. **Trace:**
GH-FR-002/004/006/007/013; GH-NFR-015; IF-06; TC-MVP-CI-001.

## ADR-013 — Receiver journal-author trust is control-plane configuration

**Status:** Accepted for the 2.3.1 recovery. **Context:** The reusable receiver
accepted a target-supplied `CODEX_TRUSTED_JOURNAL_AUTHORS` secret, allowing the
untrusted result side to influence which source-journal markers establish
admission, receipt, and forwarding state. Several target calls also omitted that
secret. **Decision:** The immutable control-plane compatibility unit owns
`config/codex-result-trust.json`. GitHub associates the normal `github` context
inside a reusable workflow with its caller, so the receiver must not use
`github.workflow_sha` or a caller checkout to locate policy. Instead, the
immutable reusable workflow invokes
`Young-Consultations/.github/actions/codex-result-receiver` at its own release
tag. That composite action executes the receiver script and policy from one
self-pinned control-plane commit; live verification requires the workflow and
action refs to resolve to the same commit. Targets supply only
`CODEX_RESULT_TOKEN`, the narrowly scoped result-delivery credential. An empty
or malformed allowlist denies all results.
**Alternatives:** caller-supplied allowlist; organization secret inherited by
targets; trust every comment author. **Tradeoffs:** deployment identities require a
reviewed control-plane change, eliminating target flexibility at this security
boundary. **Consequences:** release validation blocks publication until at least
one reviewed journal author is configured, and target verification rejects any
attempt to supply the policy. **Trace:** GH-FR-018; GH-NFR-009; GH-OR-007;
GH-SR-001/005; RI-MVP-01; TC-FR-018.

## ADR-014 — Preserve 2.3.0 and publish a fail-closed patch recovery

**Status:** Accepted for the 2.3.1 recovery. **Context:** Commit
`c6090e5bbadcc2102a1cb91875466e9decdada1e` was reviewed as the 2.3.0
compatibility baseline, but mutable target refs, incompatible workflow shapes,
caller-controlled receiver trust, and skipped conformance mean it is not safe to
activate. **Decision:** Preserve that commit as immutable historical evidence and
prepare 2.3.1 as a new patch compatibility unit. The candidate may remain
structurally coherent while blocked; publication additionally requires every
target's immutable adapter tag/commit, a digest-bound complete
`TC-MVP-CI-001` report through the real adapter with all prohibited effects at
zero, and a non-empty reviewed receiver trust policy. Disabled targets are
reported as not evaluated and cannot produce an organization-wide PASS.
**Alternatives:** rewrite or retag 2.3.0; enable one mutable target; treat local or
skipped tests as compatibility. **Tradeoffs:** recovery needs coordinated target
evidence before release, while history, rollback, and audit identity stay honest.
**Consequences:** mutable activation remains separate; no target is enabled and no
tag is published by the recovery candidate alone. **Trace:** GH-FR-013–015;
GH-NFR-002/009/015/017; GH-OR-005; GH-SR-002/005; TC-MVP-CI-001.

## ADR-015 — Bind conformance evidence without a containing-commit self-reference

**Status:** Accepted for the 2.3.1 recovery. **Context:** The first target
readiness pass after the control-plane recovery required a conformance report's
`adapter_revision` to equal the SHA of the adapter commit that contains that
report. Git computes a commit SHA from its tree, so changing the report to name
the SHA changes the SHA again. No finite release procedure can satisfy that
self-reference. **Decision:** A v2 conformance pin binds the compatibility SHA,
the exact organization schema/fixture blob identities, and the exact target
workflow/adapter/harness blob identities. Its `adapter_revision` is the SHA-256
of canonical pin contents with that field treated as null; the pin and report
must not include themselves in the bound target-file set. The report records
that pin revision. Independently, the registry records the immutable adapter tag,
the commit to which the tag resolves, and the report SHA-256. Live verification
recomputes every binding at the tag before accepting evidence.
**Alternatives:** report predicts its containing commit; accept an unbound local
report; record only a mutable branch; trust a human-entered commit without
resolving the tag. **Tradeoffs:** consumers maintain one explicit pin manifest
and the verifier performs additional read-only file checks, but evidence is both
constructible and content-addressed. **Consequences:** target evidence can be
generated before its final commit identity exists without weakening the later
tag-to-commit or report-digest checks; self-including pins/reports and substituted
files fail closed. **Trace:** GH-FR-013–015; GH-NFR-002/009/015/017; GH-OR-005;
TC-MVP-CI-001.

## ADR-016 — Prove adapter behavior executably and observe branch ownership directly

**Status:** Accepted for the 2.3.1 recovery. **Context:** The first consumer
target pass found that compatibility verification searched the thin workflow
wrapper for idempotency keywords even though the exact executable behavior is
implemented in the separately pinned adapter. Comments could satisfy that
search, while a valid wrapper without those comments would fail. The same pass
also found that adapter preflight listed pull requests but did not independently
observe whether the deterministic branch already existed; an orphaned branch
could therefore reach Codex before publication failed closed. **Decision:**
Static workflow verification proves only the exact two-input dispatch and
receiver boundary. Idempotency, ownership, create-race, and failure behavior are
accepted only through the complete shared oracle executed against the exact
adapter and harness blobs in the non-recursive conformance pin. Adapter
preflight observes both branch existence and all pull requests before Codex.
Branch/PR disagreement, including an orphaned branch or a PR whose branch is
missing, returns `ambiguous-rejected` without executor or publication effects.
Create-race reconciliation repeats both observations. **Alternatives:** retain a
comment-sensitive keyword gate; search arbitrary source text for tokens; infer
branch state from pull requests; allow Codex to rerun and rely on a later push
failure. **Tradeoffs:** preflight performs one additional read-only GitHub query,
and evidence generation must retain executable ownership scenarios, but the
gate now tests the behavior it claims. **Consequences:** wrapper comments cannot
manufacture idempotency assurance; the pinned adapter is mandatory evidence;
orphaned remote state fails before paid execution. **Trace:** GH-FR-009/013–015;
GH-QR-007; IF-06/IF-08; TC-MVP-CI-001.
