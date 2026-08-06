# Glossary

| Term | Definition |
| --- | --- |
| Acceptance criteria | Observable conditions that demonstrate a requirement is satisfied. |
| AI-assisted SDLC | Governed use of AI to support lifecycle work while humans retain consequential authority. |
| Approval provenance | Durable evidence identifying what was approved, by whom, under which authority, and when. |
| Approval ID | Immutable identity of one human authorization record bound to a source issue, executable revision digest, and target. |
| Artifact integrity | Evidence that an artifact is authentic and unchanged from its approved form. |
| Bounded AI executor | AI agent restricted by explicit authorization, scope, data, permissions, and review requirements. |
| Canonical contract | Authoritative, versioned representation shared across repository boundaries. |
| ChatGPT | Conversational AI surface that may assist humans with proposals but is not an execution authority. |
| Codex | Bounded AI coding executor invoked only within target-owned authorized execution. |
| Compatibility unit | Interdependent control-plane artifacts released and adopted together. |
| Control plane | This repository's shared policy, contract, registration, routing, and verification subsystem. |
| Correlation ID | Trace identifier associating related records; it is not the delivery idempotency key. |
| Delivery ID | Immutable identity of one logical approved delivery, preserved across retries. |
| Result ID | Stable identity used to recognize repeat delivery of the same canonical execution result; a conflicting result under the same delivery is ambiguous. |
| Revision digest | Deterministic digest of the executable issue content and selected target to which human approval is bound. |
| Draft pull request | Reviewable, explicitly non-final publication of proposed changes. |
| Exactly-once externally visible effect | At most one managed branch and open draft PR for a delivery despite possible repeated execution attempts. |
| Fail closed | Refuse execution or side effects when authorization, validity, compatibility, or state is uncertain. |
| GitHub Actions | GitHub workflow automation service used for validation, routing, and target execution coordination. |
| GitHub App | Installable GitHub identity with explicitly scoped repository permissions. |
| GitHub Issues | Authoritative durable work identities under the assumed operating model. |
| GitHub Projects | Portfolio planning/reporting projection that cannot independently authorize work. |
| Human authority | Exclusive human responsibility for approval, consequential review, merge, and production authorization. |
| Idempotency | Repeating the same logical delivery does not create additional externally visible publication effects. |
| Immutable reference | Commit digest or protected release identity whose content cannot change. |
| Implementation mode | Explicit mode permitting bounded target execution and draft-only proposed change publication. |
| Least privilege | Granting only the permissions, resources, and duration necessary for an authorized operation. |
| OIDC | OpenID Connect federation used to obtain short-lived credentials without stored long-lived secrets. |
| Organization control repository | Repository that owns shared standards and interfaces rather than application features. |
| Producer | Authorized repository/domain that presents canonical approved work to the router. |
| Registered target | Explicitly governed repository eligible to receive compatible authorized execution input. |
| Repository registry | Authoritative target identity, eligibility, capability, policy, and enablement catalog. |
| Requirement baseline | Approved, versioned set of requirements governing downstream lifecycle work. |
| Router | Control-plane boundary that validates, authorizes, selects, and delivers; it does not execute target changes. |
| SBOM | Software bill of materials identifying components in a released software artifact. |
| SLI | Service-level indicator: a measured aspect of service behavior. |
| SRS | Software Requirements Specification. |
| Target | Independently owned repository that validates and executes an authorized input locally. |
| Task contract | Canonical representation of governed work and its authoritative identity/metadata. |
| Verification method | Inspection, analysis, demonstration, or test used to establish requirement conformance. |
| Verification mode | Explicit read-only integration mode that invokes no AI implementation and publishes no change. |
| Work state | Canonical source lifecycle value: proposed, approved, queued, executing, completed, failed, withdrawn, cancelled, or superseded. Repository labels are only projections of this meaning. |
| Workflow dispatch | GitHub Actions event used to request a target workflow; acceptance may be ambiguous during faults. |
| Young Consultations | GitHub organization operating the modular governed AI-assisted delivery platform. |
