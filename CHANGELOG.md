# Changelog

## 0.3.0a2

### Multi-model research composition

- Added immutable logical model candidates with exact upstream candidate inputs, optional program/hypothesis/experiment provenance, and one selected candidate per logical model.
- Added first-class composition experiments for controlled ablation and meta/composition-model comparisons between two immutable candidates of the same target model.
- Kept model dependencies (`input`) separate from flat informational relations (`correlated`, `complementary`, `alternative`) and from the scientific hypothesis hierarchy.
- Added candidate/composition CLI commands and validation of candidate ownership and declared model-input relationships.
- Added PyPI project URLs for repository, documentation, issues, and changelog.
- Replaced PyPI-unsafe relative README documentation links with canonical absolute links and added release-link regression tests.
- Updated research-governance, bounded-research, getting-started, and public-API documentation for the current contracts.

### Hierarchical research programs and model structure

- Replaced Automo-owned research milestones with explicit research programs and falsifiable hypothesis governance; project roadmap/milestone direction is now treated as external GetDone/project context.
- Added a research model graph supporting independent models, submodel/meta-model `input` composition, and non-dependency `correlated`, `complementary`, and `alternative` relationships.
- Added model-scoped and cross-model hypotheses with local/parent/system objectives and committed evaluation depth.
- Added program → hypothesis → experiment provenance to automated research plans and generated capability requests/results.
- Replaced milestone CLI/guidance flows with model and hypothesis commands (`model-add`, `model-relation-add`, `hypothesis-create`, `hypothesis-activate`, `hypothesis-tree`, `hypothesis-conclude`).

### Agent research governance and safety

- Added `automo guidance` and a packaged task-specific research guidance pack.
- Added diagnosis, multiple-testing/selection-bias, early-stopping, meta-model ablation/OOF, refresh decision, and agent-adherence guidance.
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
- Switched the active development, CI, dependency, Python-environment, and build workflow to uv; packaging now uses the `uv_build` backend with modern PEP 621 metadata.
- Simplified one-command developer bootstrap to `uv sync` plus standard pre-commit hook installation.
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
