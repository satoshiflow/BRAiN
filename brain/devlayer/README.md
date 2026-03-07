# BRAiN Dev Layer

## Purpose

The Dev Layer is BRAiN's internal development and repair organ.

It integrates OpenCode as a first-class subsystem for:
- development
- repair
- controlled evolution

This layer exists to improve BRAiN continuously without breaking core authority boundaries.

## Authority boundary

OpenCode is inside BRAiN, but it is not BRAiN Core authority.

BRAiN Core retains authority over:
- identity
- mission control
- governance
- runtime resource control
- production release decisions

## Roles

- OpenCode: implementation and repair runtime.
- GOTT: development supervisor and orchestration authority for Dev Layer operations.
- BRAiN Core: sovereign runtime and governance authority.

## Interfaces (initial)

- Dev requests (feature/refactor/cleanup)
- Repair requests (bug/hardening/regression fixes)
- Diagnostic requests (root-cause analysis)
- Patch requests (scoped code changes)

## Scope in Local Micro profile

The Dev Layer is optimized for small local systems:
- modular operations
- lightweight tooling
- API-contract-first approach
- no mandatory heavy local model runtime
