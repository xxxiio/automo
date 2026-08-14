---
template: project-context
template_version: 3.0.0
template_digest: "d900f10edc73a83001165e84858e129d1bbbbc011e18fa9deedb4dd328d329a3"
project_owned: true
record_contract: project-context
record_schema_version: 1
status: current
---

# Project Context: getdone-mr

## Purpose

Provide a standalone, deterministic, evidence-driven package for iterative model research.

## Users and stakeholders

- Researchers and engineers comparing predictive models and feature sets.
- Maintainers reviewing experiment evidence and roadmap decisions.

## Architecture summary

The Python package loads immutable research objectives and experiment specifications from project-owned YAML. It validates data and capability prerequisites, executes bounded experiment runners, persists immutable run evidence, and will later diagnose results and commit the next experiment. GetDone is not a runtime requirement; project-local GetDone records govern development of this repository.

## Important boundaries

- `getdone-mr` owns research contracts, execution, evidence, and model-selection decisions.
- GetDone source code is not bundled and is used only as a development workflow tool or optional adapter.
- Out-of-sample evidence must remain separate from fitting and validation.

## Supported platforms and environments

- Python 3.11 or newer.
- Local filesystem execution in the current development milestone.

## Canonical commands

- `getdone-mr`
- `pytest`
- `getdone-validate-project`

## Non-negotiable constraints

- One committed experiment is executed per research iteration.
- Missing data sources produce explicit blockers; no silent fallback is allowed.
- Existing run directories are immutable.
- Validation and out-of-sample evidence are stored separately.
- GetDone must remain optional for package users.

## Current priorities

1. Complete reproducible fitting and evaluation evidence.
2. Add structured diagnosis and deterministic next-experiment transitions.
3. Add bounded model and feature research.
4. Add optional GetDone-assisted capability delegation.

## Known risks

- The initial local fixture is intentionally small and demonstrates contracts rather than statistical validity.
