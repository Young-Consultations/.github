# Architectural Decision Records

These prospective records govern architecture rather than merely describing current code. Open questions require approved follow-up and do not relax the decision.

## ADR-001 — Policy-centric clean architecture

**Context:** Governance semantics must survive workflow/runtime rewrites. **Decision:** Keep domain policy and use cases inward of workflow, transport, storage, schema-engine and telemetry adapters. **Alternatives:** workflow-script-centric logic; shared target library. **Tradeoffs:** more explicit interfaces and mapping, but pure testability and replaceability. **Consequences:** GitHub expressions and API response shapes cannot enter the domain. **Open questions:** packaging/deployment split.

## ADR-002 — One canonical, closed, versioned language

**Context:** Independent repositories otherwise drift into bilateral formats. **Decision:** Define canonical task, execution input and result contracts, validate exact versions at every boundary, and reject unknown fields unless a future contract explicitly defines extension semantics. **Alternatives:** permissive envelopes; consumer inference. **Tradeoffs:** coordinated additions versus predictable meaning. **Consequences:** breaking changes create a major; supported historical artifacts remain immutable. **Open questions:** future extension-envelope policy.

## ADR-003 — Human approval and target-owned execution

**Context:** AI must not acquire approval or production authority. **Decision:** Planning owns approval truth; control plane proves admission/routes; targets implement and publish draft proposals; humans review/merge. **Alternatives:** central executor; automation approval/merge. **Tradeoffs:** more cross-boundary evidence but strong accountability and repository autonomy. **Consequences:** control plane never modifies target code. **Open questions:** exact approval provenance/freshness contract.

## ADR-004 — At-least-once delivery with idempotent visible effects

**Context:** Cross-repository workflow delivery is not transactional. **Decision:** Preserve deterministic delivery identity and immutable payload across retries; targets preflight and create at most one managed branch and open draft PR, requerying after races. **Alternatives:** claim exactly-once transport; control-plane dedupe alone; random attempt identity. **Tradeoffs:** target complexity in exchange for recoverability. **Consequences:** duplicate reuse is canonical; ambiguity fails closed. **Open questions:** durable result reconciliation transport.

## ADR-005 — Explicit verify and implement modes

**Context:** Inferred authority can cause unintended mutation. **Decision:** Every request explicitly carries shared mode semantics: verify is read-only; implement may propose through a draft PR only. **Alternatives:** infer from prose or caller/workflow. **Tradeoffs:** strict caller coordination for a clearer security boundary. **Consequences:** mode-specific result invariants and compatibility tests. **Open questions:** additional future modes require a major compatibility assessment.

## ADR-006 — Registry-based deterministic routing

**Context:** Authorized targets/capabilities must be explicit. **Decision:** Use a reviewed, versioned registration snapshot; route only when exactly one enabled compatible target matches. **Alternatives:** convention discovery; caller-supplied workflow; dynamic broad matching. **Tradeoffs:** administrative onboarding versus predictable least privilege. **Consequences:** invalid registry blocks delivery and one target can be isolated. **Open questions:** registry owner/schema evolution.

## ADR-007 — Atomic immutable compatibility releases

**Context:** Router, schema, validator, registry format and checks are interdependent. **Decision:** Bind them in one immutable release manifest with adoption, deprecation and known-good rollback. **Alternatives:** independently version all artifacts; movable branch references. **Tradeoffs:** coordinated releases versus elimination of mixed-version ambiguity. **Consequences:** production consumers pin identities. **Open questions:** signing/attestation enforcement mechanism.

## ADR-008 — Evidence-based asynchronous outcomes

**Context:** Dispatch acknowledgement is not execution success. **Decision:** Separate attempt acknowledgement from target result; accept success only with validated target evidence. **Alternatives:** synchronous router completion; assume success on dispatch. **Tradeoffs:** reconciliation complexity versus honest status. **Consequences:** pending/uncertain are first-class states. **Open questions:** callback, polling, or artifact-based result channel.
