# Automo Roadmap

Automo is preparing the `0.3.0a2` public alpha, extending the first public alpha with multi-model research governance and composition research.

## Completed foundation

The current package includes:

- deterministic research contracts with explicit validation and OOS boundaries;
- structured decisions, feature disposition, temporal stability, and promotion recommendations;
- optional bounded capability workflows;
- generic data/feature/model runtime contracts;
- immutable model registry, calibration lineage, benchmark history, and lifecycle events;
- dataset-agnostic refresh partitions and model pools;
- fit → validation → refresh-OOS governance for recalibration and retraining;
- bounded automated research with explicit candidate budgets and sealed research-OOS caps;
- custom trainers/evaluators and injected project services;
- structured model outputs;
- composable model graphs with leakage-safe first-level cross-fitting for downstream/meta-models.

## Public alpha hardening

`0.3.0a2` is gated on:

- Automo-only package/CLI identity;
- clean wheel and sdist contents;
- one package-version source;
- explicit persisted artifact type/schema versions;
- documented public extension APIs and trust boundaries;
- fresh-project init/validate/doctor flow;
- focused synthetic onboarding examples plus one end-to-end example;
- controlled CLI errors for normal user mistakes;
- wheel and sdist clean-install smoke tests;
- Python 3.11–3.13 CI;
- pre-commit as the canonical repository-quality gate, with Ruff handling overlapping Python lint/format responsibilities;
- public-ready README, security policy, changelog, and release contract.

## Deferred until after external feedback

No further model-research feature milestone is committed before public-alpha feedback. Candidate future work includes:

- deeper nested graph cross-fitting where real projects require it;
- richer contextual/diversity model-pool selection;
- stronger statistical corrections for large adaptive research spaces;
- additional registry/storage adapters;
- deployment integrations only under a separately approved milestone.
