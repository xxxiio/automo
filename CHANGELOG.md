# Changelog

### Agent research governance and safety

- Added `.automo/` project-owned research governance with milestone plan/research modes.
- Added `automo guidance` and a packaged task-specific research guidance pack.
- Added research milestone lifecycle commands and execution guards.
- Added diagnosis, multiple-testing/selection-bias, early-stopping, meta-model ablation/OOF, refresh decision, and agent-adherence guidance.
- Added deterministic guidance-pack validation and a synthetic multi-milestone research walkthrough.
- Moved generated capability requests/results under `.automo/capabilities/` and added bounded GetDone handoff briefs without mutating `.agent/`.

## 0.3.0a1

- Added GetDone-style `.project-agent/` research-guidance composition and lock verification, generalized model provenance/pool extension contracts, and consumer compatibility hardening. — First public alpha

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
- Seven small synthetic onboarding examples, including compact end-to-end registry and agent-guidance walkthroughs.

### Changed

- The package and CLI now use the Automo identity exclusively.
- Package version metadata has one source of truth.
- Restored the PPW-derived Poetry Core packaging backend while retaining modern PEP 621 project metadata and uv-based development/test environments.
- Added PPW-style one-command developer bootstrap that synchronizes dev dependencies and installs/pre-provisions the Git pre-commit hook.
- Pre-commit is the canonical repository-quality gate; it combines repository/configuration hygiene with Ruff lint/format, and CI runs the same hook configuration.
- Runtime-generated runs, recommendations, build outputs, and local egg-info are excluded from the clean source tree/release artifacts.
- Wheel and sdist clean-install checks are release gates.

### Security

- Documented that plugins, trainers, evaluators, codecs, calibrators, injected services, model artifacts, and delegated workflows are trusted-code boundaries and are not sandboxed.

### Known limitations

- Deep recursively nested model-output cross-fitting is intentionally rejected by the first public graph contract.
- The alpha does not provide deployment, distributed training, unrestricted AutoML, or a sandbox for third-party extensions.

## Internal development history

The `0.2.0a1`–`0.2.0a5` builds were pre-public development snapshots used to establish the runtime, registry, refresh, bounded-research, and model-graph architecture. They are not part of the supported public release line.
