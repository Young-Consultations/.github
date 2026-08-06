# AI-SDLC Control-Plane Requirements Baseline

**Baseline:** 1.0 (proposed)  
**Status:** Ready for stakeholder review  
**Authoritative input:** [`../VISION.md`](../VISION.md)  
**Scope:** `Young-Consultations/.github`

This package is the requirements baseline for the organization AI-assisted SDLC control plane. Architecture, design, implementation, tests, and backlog items shall cite requirement IDs in this package. Current code is evidence of the present state, not a constraint on the required future state.

## Document map

| Document | Authority |
| --- | --- |
| [Project requirements](project-requirements.md) | Outcomes, scope, stakeholders, goals, and product constraints |
| [Software requirements](software-requirements.md) | Normative functional, quality, operational, and security requirements |
| [Repository context](repository-context.md) | System boundary and artifact ownership |
| [Repository interfaces](repository-interfaces.md) | Organization repository contracts |
| [External interfaces](external-interfaces.md) | GitHub, AI, and third-party boundaries |
| [Traceability matrix](requirements-traceability.md) | Upstream and downstream traceability for every normative requirement |
| [Organization context](organization-context.md) | Enterprise placement and lifecycle |
| [User experience](user-experience.md) | Human-facing experience requirements |
| [Gap analysis](gap-analysis.md) | Current-to-required-state assessment |
| [Glossary](glossary.md) | Controlled vocabulary |

## Normative conventions and governance

“Shall” denotes a requirement; “should” denotes guidance; “may” denotes permission. Requirement priorities are **Must**, **Should**, or **Could**. Vision source codes are `V-ORG` (organization vision), `V-FLOW` (desired experience), `V-PRIN` (guiding principles), `V-RESP` (repository responsibilities), `V-NRESP` (non-responsibilities), `V-GUARD` (constraints), and `V-EVOL` (evolution strategy). Business goals `BG-01`–`BG-07` are defined in the PRD.

Approval requires the organization owner, engineering lead, security owner, and control-plane maintainer. Changes use pull-request review, impact analysis, traceability updates, and semantic baseline versions. Conflicts resolve in this order: approved vision, approved requirements baseline, downstream specifications, current implementation.

## Global assumptions requiring validation

Other repositories were unavailable. Their interfaces are inferred from the vision, registry, schemas, workflows, and repository documentation. GitHub Issues are assumed to remain the executable-work source; Projects are planning/reporting only; targets own execution; immutable references are available; draft pull requests are the only automated publication; and humans retain merge and production authority. Assumptions are not authorization: unresolved trust, compatibility, identity, or state shall fail closed.
