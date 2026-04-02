# AXE / ControlDeck v3 / Paperclip Surface Responsibilities

Status: Draft v1  
Owner: BRAiN Product + Runtime  
Date: 2026-04-01

## 1. Purpose

This document defines the authoritative responsibility split for the three human-facing surfaces around BRAiN:

- `AXE`
- `ControlDeck v3 (CD3)`
- `Paperclip UI / MissionCenter`

Goal:

- avoid duplicated mental models
- avoid governance drift
- avoid a second runtime authority
- make operator behavior predictable and trainable

## 2. Core Rule

There is only one runtime authority:

- `BRAiN backend runtime`

There is only one canonical execution record:

- `SkillRun`

There is only one canonical bounded external dispatch object:

- `TaskLease`

All three surfaces must respect this and may not create a competing execution truth.

## 3. Surface Roles

## 3.1 AXE

Primary role:

- intent ingress
- conversational control surface
- fast operator intervention
- ad-hoc execution requests
- quick approval / escalation / incident reactions

Best used for:

- “Do this now”
- “Why did BRAiN choose this?”
- “Pause / retry / escalate this run”
- “Launch this task through a worker”

Not used for:

- broad policy administration
- secret/config governance at scale
- operational team management of a full agent company
- ERP workflows

Output posture:

- action-oriented
- short-cycle
- operator-focused

## 3.2 ControlDeck v3

Primary role:

- governance cockpit for BRAiN itself
- runtime control
- policy and override management
- approval and audit visibility
- explainability of effective decisions
- system health / safety / drift / incident diagnostics

Best used for:

- “Which policy/override decided this?”
- “What is the effective runtime config?”
- “Which executor is enabled?”
- “Approve or reject a change request”
- “Review audit timeline and control-plane events”

Not used for:

- day-to-day company task operations
- full business team workboard management
- being the primary ticketing UI for external executor organizations

Output posture:

- governance-oriented
- system-centric
- explainable and auditable

## 3.3 Paperclip UI / MissionCenter

Primary role:

- bounded operations console for agent organizations
- operational visibility into goals, issues, agents, heartbeats, work queues
- human observation and intervention inside the business-ops layer

Best used for:

- seeing active agent teams and work distribution
- understanding operational backlog and execution progress
- following agent activity in the “company” view
- operational triage and bounded intervention requests

Not used for:

- policy source-of-truth
- direct runtime override management
- secret/config control-plane management
- direct unrestricted connector governance

Output posture:

- operational
- team/workflow-oriented
- business process visibility

## 4. Human Task Mapping

## 4.1 Use AXE when...

- the user starts from language/intent
- the operator wants a quick action
- a run needs immediate human intervention
- the operator wants a compact explanation in context

## 4.2 Use CD3 when...

- governance or policy is involved
- a runtime decision must be inspected or changed through approved flows
- the operator needs system-level traceability
- secrets, runtime controls, or registry state are being reviewed

## 4.3 Use Paperclip when...

- the operator wants to see operational company activity
- the operator needs the agent-team/workboard perspective
- the operator wants to understand what a bounded external executor organization is doing right now

## 5. Allowed Action Classes by Surface

## 5.1 AXE allowed actions

- create intent / start task / dispatch worker
- request explanation
- request retry / cancel / escalate
- perform bounded approvals when routed through backend governance

## 5.2 CD3 allowed actions

- create/approve/reject runtime change requests
- inspect effective runtime decisions
- manage policy/override surfaces
- inspect audit/control-plane timelines
- trigger governed emergency mode actions

## 5.3 Paperclip allowed actions

- browse operational structures and activity
- request bounded interventions
- request escalation or approval
- perform safe operational actions that are explicitly routed through BRAiN governance

## 6. Forbidden Action Classes by Surface

## 6.1 AXE forbidden

- becoming ad-hoc source of runtime config truth
- bypassing approval/policy for sensitive actions

## 6.2 CD3 forbidden

- replacing the business operations UI of external executor organizations
- directly mutating external apps outside governed contracts

## 6.3 Paperclip forbidden

- direct policy mutation
- direct secret/config mutation as source-of-truth
- unrestricted connector calls
- direct governance bypass against BRAiN runtime decisions

## 7. Navigation / Linking Rules

Required link posture:

- `AXE -> CD3`: for governance edits and explainable decision review
- `CD3 -> Paperclip`: for operational drill-down into external executor work
- `Paperclip -> CD3`: for approval/governance/escalation actions

Important:

- links carry context, not authority
- authority remains in BRAiN backend

## 8. Labels and Shared Language

The following terms must be used consistently across surfaces:

- `Mission`
- `SkillRun`
- `TaskLease`
- `Executor`
- `Approval`
- `Decision ID`
- `Correlation ID`

Paperclip-native nouns may still exist (`Company`, `Project`, `Issue`, `Agent`) but must be linked back to BRAiN context where relevant.

## 9. UX Implication for Operators

Operators should be able to answer these questions quickly:

- “What is BRAiN doing?” -> AXE / CD3
- “Why is BRAiN allowed to do this?” -> CD3
- “What is the external agent company doing right now?” -> Paperclip
- “Where do I intervene safely?” -> AXE for quick action, CD3 for governed action, Paperclip for bounded operational request

## 10. Acceptance Criteria

This responsibility split is successful when:

1. no surface duplicates another surface’s primary mission
2. operators can name where a task belongs without hesitation
3. governance actions remain visibly centralized in CD3/BRAiN
4. Paperclip adds operational visibility without becoming a second control plane
