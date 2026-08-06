# User Experience Requirements

## Experience strategy

Governance must make the safe path the easiest understandable path. Experiences serve occasional contributors, maintainers, reviewers, operators, and auditors. They shall use progressive disclosure: concise required actions first, rationale and advanced recovery next. UX does not weaken authorization or make AI output authoritative.

| ID | Requirement (priority and rationale) | Measurable acceptance criteria | Source / verification / traceability |
| --- | --- | --- | --- |
| GH-UX-001 | **Issue intake (Must):** Issue templates shall gather outcome, authoritative source, scope/non-scope, owner, requirement trace, acceptance evidence, dependencies, risk/data classification, and approval state without implying that submission is approval. | Required fields block Ready; five representative users complete a valid request with at least 80% first-pass success; AI text is visibly a proposal. | V-FLOW/V-PRIN; form validation and usability test; BG-01/BG-07, `TC-UX-001`. |
| GH-UX-002 | **PR review (Must):** Pull-request guidance shall expose intent, requirement/interface impact, risk, tests, security, compatibility, adoption, and rollback and shall label automation-created PRs as draft proposals. | Reviewers locate every category within two minutes; missing evidence is detected; automation cannot clear draft/merge. | V-FLOW/V-GUARD; usability and permission test; BG-02/BG-04, `TC-UX-002`. |
| GH-UX-003 | **Onboarding (Should):** A role-based onboarding path shall lead from purpose and boundaries to contract use, local validation, integration, troubleshooting, support, and rollback. | A new integrator completes the documented example and identifies prohibited actions within 30 minutes without private help. | V-PRIN/V-EVOL; moderated task test; BG-07, `TC-UX-003`. |
| GH-UX-004 | **Discoverability/navigation (Must):** Repository entry points shall link the vision, requirements baseline, contracts, interfaces, security, contribution, release, and operations guidance with one authoritative location for each topic. | Each item is reachable from the root entry point in at most two links; link and duplicate-authority audit passes. | V-PRIN; information-architecture/link test; BG-03/BG-07, `TC-UX-004`. |
| GH-UX-005 | **Contribution flow (Should):** Contributors shall receive a visible sequence from issue readiness through branch/PR checks, review, release impact, and closure, including actionable failure remediation. | Five representative change scenarios identify next step and owner with at least 90% task success. | V-FLOW/V-EVOL; journey walkthrough; BG-06/BG-07, `TC-UX-005`. |
| GH-UX-006 | **Automation discoverability (Must):** Every user-invocable or required automation shall document purpose, trigger, inputs, permissions, effects, non-effects, expected duration, outputs, common failures, retry safety, and support owner. | Inventory has no undocumented automation; users correctly distinguish verify from implement and safe from unsafe retry. | V-GUARD/V-RESP; documentation audit/usability test; BG-04/BG-07, `TC-UX-006`. |
| GH-UX-007 | **Consistency and feedback (Should):** Templates, statuses, identifiers, priorities, failure terms, and help patterns shall use the glossary consistently and communicate success, pending, rejection, and failure without color alone. | Terminology scan finds no conflicting normative labels; accessibility review and eight-state comprehension test achieve 90% correct interpretation. | V-PRIN; content/accessibility test; BG-03/BG-07, `TC-UX-007`. |
| GH-UX-008 | **Recovery experience (Must):** Failure messages shall state what failed, whether side effects may exist, safe next action, evidence/correlation identity, and responsible owner without exposing sensitive data. | Fault scenarios provide all five elements; users recover representative failures without creating a duplicate effect. | V-RESP/V-GUARD; fault-injection usability test; BG-04/BG-05, `TC-UX-008`. |

## Core journeys

1. **Contributor:** find standard → create traced issue → satisfy Ready → propose PR → respond to deterministic gates → obtain human review.
2. **Target integrator:** understand boundary → select immutable contract → implement local verification and idempotency → pass read-only compatibility → request enablement → adopt release.
3. **Reviewer:** confirm approval and scope → inspect requirement/risk/evidence → distinguish generated proposal → approve or reject → merge only with authority.
4. **Operator:** locate correlation identity → classify state → isolate target if needed → reconcile evidence → retry unchanged delivery or roll back → record outcome.
5. **Auditor:** select delivery/release → traverse durable links → establish actors, decisions, versions, permissions, attempts, and outcome.

No journey may rely on color, undocumented organization knowledge, direct default-branch changes, or automatic acceptance.
