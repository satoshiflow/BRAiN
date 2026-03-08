# Builder as Skill Consumer Specification (v1)

Status: Baseline implemented and stabilized (2026-03-08)  
Scope: Standardizes builders and domain generators as orchestrators over skills instead of direct feature runtimes.

## Purpose

Builders such as `webgenesis` and `course_factory` must become orchestrators of `SkillRun` graphs.

They may compose skills, but should not embed a separate hidden runtime.

## Repo Alignment

- Current builders: `backend/app/modules/webgenesis/`, `course_factory/`, `deployment/`, `dns_hetzner/`

## Ownership Boundaries

Builders own:
- domain-specific orchestration
- artifact assembly plans
- user-facing domain semantics

Builders do not own:
- raw capability execution
- governance gate bypasses
- canonical provider routing

## Builder Contract

Every builder action must map to one or more governed `SkillRun`s.

Examples:
- `course_factory.generate_outline`
- `webgenesis.build_site`
- `webgenesis.deploy_site`
- `dns.apply_record`

Each builder step must have:
- referenced `skill_key`
- frozen `skill_version`
- input/output contract
- audit correlation
- `tenant_id`
- `skill_run_id`

## Artifact Graph

Builders may maintain artifact graphs, but every executable node in that graph must be backed by a `SkillRun` or explicit non-executable assembly step.

## API Surface

- builder-facing APIs may remain domain-specific
- execution beneath builder APIs must translate into `SkillRun` creation and tracking

## Audit and Event Requirements

- `builder.skillrun.created.v1`
- `builder.artifact.assembled.v1`
- `builder.deploy.requested.v1`

Durable audit required for:
- deployment-affecting actions
- DNS/infrastructure-affecting actions
- governed publication actions

## PostgreSQL vs Redis vs EventStream

### PostgreSQL
- artifact assembly metadata
- builder-to-skill mapping records

### Redis
- transient build progress

### EventStream
- builder orchestration lifecycle

## Legacy Compatibility

- Existing direct service calls in builders are compatibility implementations only.
- New builder features must target skill orchestration first.
- Existing builder endpoints may remain as wrappers, but canonical execution write ownership must move to `SkillRun`.

## Done Criteria

- builders are documented as skill consumers
- builder graphs distinguish executable skill nodes from assembly-only nodes
- deployment and infra operations remain governance-protected

## Implementation Status

- `course_factory` and `webgenesis` builder routes now operate as wrappers over governed `SkillRun` execution paths
- builder responses expose `skill_run_id` where canonical execution ownership is active
- external builder-controlled flows terminalize canonical runs through `skill_engine.finalize_external_run(...)`
- wider builder, governance, and orchestration regression slices passed after stabilization
