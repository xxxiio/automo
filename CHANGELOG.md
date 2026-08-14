# Changelog

## 0.3.0a1 — First public alpha

### Added

- Generic custom `ModelTrainer`/`Evaluator` contracts with injected project services.
- Structured model outputs and composable model graphs.
- Leakage-safe cross-fitted upstream outputs for first-level downstream/meta-model training.
- Immutable filesystem model registry, calibration lineage, benchmark history, and lifecycle events.
- Dataset-agnostic refresh partitions, model pools, recalibration/retraining governance, and refresh history.
- Bounded automated research with explicit interventions, budgets, candidate fingerprints, validation shortlisting, and sealed research-OOS limits.
- Versioned public persistence envelopes with `artifact_type` and `schema_version`.
- Minimal fresh-project scaffolding through `automo init`.
- Public API, security, getting-started, trainer/graph, registry, refresh, and research documentation.
- Six small synthetic onboarding examples, including a compact end-to-end registry walkthrough.

### Changed

- The package and CLI now use the Automo identity exclusively.
- Package version metadata has one source of truth.
- Pre-commit is the canonical Ruff lint/format quality gate; CI runs the same hooks.
- Runtime-generated runs, recommendations, build outputs, and local egg-info are excluded from the clean source tree/release artifacts.
- Wheel and sdist clean-install checks are release gates.

### Security

- Documented that plugins, trainers, evaluators, codecs, calibrators, injected services, model artifacts, and delegated workflows are trusted-code boundaries and are not sandboxed.

### Known limitations

- Deep recursively nested model-output cross-fitting is intentionally rejected by the first public graph contract.
- The alpha does not provide deployment, distributed training, unrestricted AutoML, or a sandbox for third-party extensions.

## Internal development history

The `0.2.0a1`–`0.2.0a5` builds were pre-public development snapshots used to establish the runtime, registry, refresh, bounded-research, and model-graph architecture. They are not part of the supported public release line.
