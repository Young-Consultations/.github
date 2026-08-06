# AI-SDLC Control-Plane Architecture

**Status:** Proposed; non-authoritative pending approval of the [requirements baseline](../requirements/README.md).

This directory is the proposed implementation-independent design for `Young-Consultations/.github`. Read [the vision](../VISION.md) and [requirements baseline](../requirements/README.md) first. Once the baseline receives its required stakeholder approvals and this suite is approved against it, the authority order will be **Vision → Requirements → Architecture → Implementation**. Until then, current approved specifications and implementation remain authoritative for implemented behavior.

## Document map

| Concern | Document |
| --- | --- |
| Architecture and quality attributes | [Software Architecture](SoftwareArchitecture.md) |
| System decomposition | [High-Level Design](HighLevelDesign.md) |
| Modules and ports | [Low-Level Design](LowLevelDesign.md) |
| Components | [Component Design](ComponentDesign.md) |
| Concepts and invariants | [Domain Model](DomainModel.md) |
| Commands, events and information movement | [Data Flow](DataFlow.md) |
| All boundary contracts | [Interface Architecture](InterfaceArchitecture.md) |
| External collaborators and unknowns | [Integration Architecture](IntegrationArchitecture.md) |
| Ownership | [Repository Boundaries](RepositoryBoundaries.md) |
| Workflow interactions | [Sequence Diagrams](SequenceDiagrams.md) |
| Lifecycles | [State Models](StateModels.md) |
| Decisions and tradeoffs | [Architectural Decisions](ADR.md) |
| Security | [Security Architecture](SecurityArchitecture.md) |
| Conceptual runtime topology | [Deployment Architecture](DeploymentArchitecture.md) |
| Operational visibility | [Observability Architecture](ObservabilityArchitecture.md) |
| Failures and recovery | [Error Handling](ErrorHandling.md) |
| Policy/configuration | [Configuration Architecture](ConfigurationArchitecture.md) |
| Safe evolution points | [Extension Architecture](ExtensionArchitecture.md) |
| Vision-to-implementation coverage | [Architecture Traceability](ArchitectureTraceability.md) |

## Interpretation rules

- Responsibilities and contracts are intended to become normative after baseline and architecture approval; examples and diagrams explain them.
- External repository internals are deliberately unspecified. `Known`, `Assumed`, and `Unknown` integration facts have distinct meanings.
- Open questions block invention, not all progress: implementations may proceed behind a port while preserving fail-closed behavior.
- Architecture changes require vision/requirement trace, affected interfaces, compatibility/security assessment, tests, adoption, and rollback consideration.
