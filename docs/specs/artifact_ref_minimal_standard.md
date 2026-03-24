# Artifact Reference Minimal Standard

Status: Epic 1 implementation contract

## Purpose

Provide a stable minimal reference shape for artifacts before a full artifact registry exists.

## Reference Shape

Each artifact ref is a JSON object with:

- `artifact_key`: stable identifier or external id
- `artifact_type`: semantic class such as `input`, `output`, `evidence`, `review`, `comparison`, `definition`, `example`, `builder`, `contract`, `adapter_test`
- `uri`: optional local or remote locator
- `content_type`: optional MIME-like hint
- `checksum_sha256`: optional integrity hash
- `metadata`: optional free-form map

## Standard Field Names

- `input_artifact_refs`
- `output_artifact_refs`
- `evidence_artifact_refs`
- `review_artifact_refs`
- `comparison_artifact_refs`
- `definition_artifact_refs`
- `example_artifact_refs`
- `builder_artifact_refs`
- `contract_artifact_refs`
- `adapter_test_artifact_refs`

## Rules

- Use JSON arrays of artifact-ref objects.
- Empty list is preferred over `null`.
- Artifact refs are evidence and provenance only; they do not imply execution authority.
- `SkillRun` and `EvaluationResult` must use stable refs, not mutable implicit paths only.
