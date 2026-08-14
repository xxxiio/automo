---
template: roadmap
template_version: 2.0.0
template_digest: "938b804e31855ad2d8e66c8a04f659b8750c6c3dbe1480242264f7cc5c1732ba"
project_owned: true
record_contract: roadmap
record_schema_version: 1
status: current
current_milestone: MILESTONE-0013
---

# Project Roadmap

## Product outcome

Automo is the successor product identity for GetDone MR after MILESTONE-0007. Historical completed milestones retain their original GetDone MR wording as evidence of the package state at the time. Automo stands for automated model optimisation and lifecycle research. GetDone remains an optional workflow integration, not part of the primary product name.

Automo should provide complete reusable model-research infrastructure by default: data access contracts, feature computation, model fitting, evaluation, model registries, calibration, model pools, recurring refresh, dynamic selection, and bounded automated research. User packages should supply thin domain plugins and may replace individual subsystems through narrow interfaces when needed.

## Ordering principles

1. Complete core research correctness before adding search breadth.
2. Keep GetDone optional for users while using its project workflow to develop this repository.
3. Preserve point-in-time data integrity and sealed out-of-sample evidence.
4. Prefer deterministic and independently testable capabilities.

## Milestones

### MILESTONE-0001 — Deterministic research foundation

- **Status:** completed
- **Outcome:** Experiment contracts, prerequisite blockers, CLI inspection, and optional integration boundaries exist.
- **Why now:** All execution depends on stable contracts.
- **Depends on:** none

#### Scope

- Objectives, experiments, prerequisite checks, and standalone CLI.

#### Non-goals

- Model fitting.

#### Exit criteria

- [x] EC-001: Standalone contracts and prerequisite checks pass.

#### Evidence

- EC-001: `src/getdone_mr/contracts.py`, `src/getdone_mr/prerequisites.py`, and tests.

#### Next milestone

MILESTONE-0002

### MILESTONE-0002 — Reproducible fitting and evaluation

- **Status:** completed
- **Outcome:** Baseline and candidate runs execute against frozen splits and produce immutable fitting, validation, and OOS evidence.
- **Why now:** Defensible decisions require reproducible execution before diagnosis or search.
- **Depends on:** MILESTONE-0001

#### Scope

- Dataset snapshots, split manifests, model runners, separate evaluation stages, and run evidence.

#### Non-goals

- Broad search and production promotion.

#### Exit criteria

- [x] EC-001: A local fixture fits a baseline and candidate reproducibly.
- [x] EC-002: Validation and out-of-sample evidence are stored separately.
- [x] EC-003: The out-of-sample stage rejects post-freeze configuration changes.
- [x] EC-004: Run manifests include code, data, environment, seed, cost, and timing evidence.

#### Evidence

- EC-001: `runs/experiment-0001-bootstrap/manifest.json` and `tests/test_execution.py`.
- EC-002: `runs/experiment-0001-bootstrap/validation.json` and `out-of-sample.json`.
- EC-003: `freeze.json`, `evaluate-oos`, and post-freeze mutation tests.
- EC-004: `runs/experiment-0001-bootstrap/manifest.json`.

#### Next milestone

MILESTONE-0003

### MILESTONE-0003 — Diagnosis and deterministic next experiment

- **Status:** completed
- **Outcome:** Evidence produces a structured decision and exactly one falsifiable next experiment.
- **Why now:** This follows sealed evaluation.
- **Depends on:** MILESTONE-0002

#### Scope

- Decisions, findings, feature usefulness, and transition rules.

#### Non-goals

- Unbounded search.

#### Exit criteria

- [x] EC-001: Completed evidence produces a structured decision.
- [x] EC-002: Feature groups receive independent dispositions.
- [x] EC-003: Findings produce one next experiment with falsification criteria.

#### Evidence

- EC-001: `runs/experiment-0003-decision/decision.json` and `tests/test_decisions.py`.
- EC-002: `runs/experiment-0004-features/feature-dispositions.json` and `tests/test_features.py`.
- EC-003: `runs/experiment-0004-features/findings.json`, `research/experiments/EXPERIMENT-0002.yaml`, and `tests/test_findings.py`.

#### Next milestone

MILESTONE-0004

### MILESTONE-0004 — Bounded model and feature research

- **Status:** completed
- **Outcome:** Governed model and feature candidates are compared under explicit budgets.
- **Why now:** Search follows correct execution and diagnosis.
- **Depends on:** MILESTONE-0003

#### Scope

- Candidate registries, bounded ablation and search, stability, and champion/challenger recommendations.

#### Non-goals

- Unlimited AutoML or automatic deployment.

#### Exit criteria

- [x] EC-001: Search respects committed budgets and ordering.
- [x] EC-002: Promotion uses quality, stability, and operational gates.

#### Evidence

- EC-001: `runs/experiment-0006-temporal/temporal-stability.json` and `tests/test_temporal_stability.py`.
- EC-002: `recommendations/promotion-0001/recommendation.json` and `tests/test_promotions.py`.

#### Next milestone

MILESTONE-0005

### MILESTONE-0005 — Optional GetDone-assisted capability workflows

- **Status:** completed
- **Outcome:** Missing capabilities can be delegated to compatible GetDone workflows without coupling research decisions.
- **Why now:** Delegation follows a stable standalone lifecycle.
- **Depends on:** MILESTONE-0004

#### Scope

- Capability request contracts, workflow discovery, bounded paths, and resumable state.

#### Non-goals

- Required GetDone installation.

#### Exit criteria

- [x] EC-001: Standalone behavior remains unchanged without GetDone.
- [x] EC-002: Compatible workflows can fulfill and return a bounded capability request.

#### Evidence

- EC-001: standalone blocked-attempt tests and lazy optional integration status.
- EC-002: compatible injected-workflow test, immutable results, scope enforcement, protected hashes, and persisted state.

#### Next milestone

MILESTONE-0006

### MILESTONE-0006 — Release readiness for 0.1

- **Status:** completed
- **Outcome:** Accurate evidence records and a passing standalone release health gate support an initial alpha release.
- **Why now:** Core lifecycle work is complete; release confidence is the highest-priority unfinished outcome.
- **Depends on:** MILESTONE-0005

#### Scope

- Evidence audit, command contract, health gate, wheel installation, and release documentation.

#### Non-goals

- New research adapters or algorithms.

#### Exit criteria

- [x] EC-001: Roadmap evidence references are accurate.
- [x] EC-002: Canonical commands are complete.
- [x] EC-003: Standalone release health gate passes.
- [x] EC-004: Release boundary and limitations are documented.

#### Evidence

- EC-001: corrected roadmap evidence references.
- EC-002: `.agent/command-reference.md`.
- EC-003: `scripts/health_gate.py` and release-health tests.
- EC-004: `README.md` and `docs/RELEASE-0.1.md`.

#### Next milestone

MILESTONE-0007


### MILESTONE-0007 — GetDone 1.1.2 workflow contract and unified MR UX

- **Status:** completed
- **Outcome:** GetDone MR validates against GetDone dev 1.1.2 and exposes a coherent project-oriented CLI while preserving standalone deterministic research primitives.
- **Why now:** The research engine is release-complete; workflow-contract accuracy and product usability are the highest-priority approved follow-up.
- **Depends on:** MILESTONE-0006

#### Scope

- Project-record migration, unified CLI, advanced command grouping, compatibility aliases, optional dependency update, tests, and documentation.

#### Non-goals

- New model or dataset adapters, AutoML, deployment, or an MR-specific shared skill pack.

#### Exit criteria

- [x] EC-001: Project records validate against GetDone dev 1.1.2 without contract errors.
- [x] EC-002: `init`, `doctor`, `status`, `plan`, `run`, and `validate` are functional and documented.
- [x] EC-003: `run` executes exactly one legal deterministic research transition.
- [x] EC-004: Advanced primitives are grouped and legacy aliases remain compatible.
- [x] EC-005: Standalone operation remains independent of GetDone and the optional extra targets 1.1.2.
- [x] EC-006: Full tests, packaging, wheel installation, and CLI smoke gates pass.

#### Evidence

- EC-001: `.agent/skills.lock.json` and GetDone 1.1.2 project validation.
- EC-002: `src/getdone_mr/cli.py`, `src/getdone_mr/ux.py`, README, user guide, and CLI tests.
- EC-003: `test_run_executes_exactly_one_temporal_transition`.
- EC-004: grouped-command tests and hidden compatibility aliases.
- EC-005: `pyproject.toml`, integration adapter, and release-health dependency tests.
- EC-006: canonical `scripts/health_gate.py` and full test suite.

#### Next milestone

None

### MILESTONE-0008 — Extensible research runtime

- **Status:** completed
- **Outcome:** Automo supplies complete default data, feature, fitting, and evaluation infrastructure behind replaceable subsystem contracts so user packages need only a thin domain plugin.
- **Why now:** Reusable execution infrastructure should live in Automo rather than be rebuilt per domain package, and the approved rename needs a modern Python package foundation before registry/lifecycle expansion.
- **Depends on:** MILESTONE-0007

#### Scope

- Automo distribution/package/CLI rename with compatibility shim.
- Python 3.11+ package skeleton with Ruff, pytest, pre-commit, Zensical, CI, wheel/sdist gates.
- Thin `ResearchPlugin` contracts.
- Reusable data source, feature graph, model runner, and evaluation contracts/defaults.
- Project plugin loading by import path or entry point.

#### Non-goals

- Model registry/model pool lifecycle.
- Unbounded AutoML.
- Domain-specific application semantics.

#### Exit criteria

- [x] EC-001: Thin plugins can register domain data, features, objectives, metrics, and candidate models.
- [x] EC-002: Default feature computation, model running, and evaluation work without project-specific orchestration.
- [x] EC-003: Runtime subsystems remain independently replaceable.
- [x] EC-004: Reference fixture uses the same runtime interfaces as external projects.
- [x] EC-005: Metrics carry direction and scope semantics.
- [x] EC-006: Standalone operation remains independent of GetDone.
- [x] EC-007: Python 3.11+ support is declared and validated by CI configuration.
- [x] EC-008: Ruff is the canonical formatter/linter/style tool and is invoked through uv in normal development/CI.
- [x] EC-009: Zensical configuration and committed Markdown documentation are present; docs build/serve remains optional and separately runnable.
- [x] EC-010: Local, pre-commit, and CI gates share canonical Ruff/pytest/package quality commands.

#### Evidence

- EC-001: `src/automo/runtime/contracts.py`, `plugin.py`, and plugin tests.
- EC-002: `src/automo/runtime/features.py`, `builtins.py`, `project.py`, and runtime tests.
- EC-003: protocol contracts for `DataSource`, `FeatureComputer`, `ModelRunner`, and `Metric`.
- EC-004: `tests/test_runtime.py` reference fixture through `ResearchRuntime`.
- EC-005: `MetricDirection`, `MetricScope`, and metric contract tests.
- EC-006: standalone wheel/CLI smoke and optional GetDone integration tests.
- EC-007: `requires-python = ">=3.11"` and Python 3.11/3.12/3.13 CI matrix.
- EC-008: Ruff configuration, uv-based local commands, Ruff pre-commit hooks, and uv-based CI enforcement.
- EC-009: `zensical.toml`, `docs/`, and the separate `docs` optional dependency.
- EC-010: `.pre-commit-config.yaml`, uv-based `.github/workflows/ci.yml`, `pyproject.toml`, `scripts/health_gate.py`, `CONTRIBUTING.md`, and `SECURITY.md`.

#### Next milestone

MILESTONE-0009

### MILESTONE-0009 — Model registry and lifecycle

- **Status:** completed
- **Outcome:** Automo owns a reusable, Git-friendly filesystem model registry with immutable model identity, complete training lineage, independent calibration lineage, append-only benchmark history, validated lifecycle transitions, and model inspection CLI.
- **Why now:** Reusable fitting became available in MILESTONE-0008; persistent model identity and evidence history are the prerequisite for model pools, recalibration, refresh, and dynamic selection.
- **Depends on:** MILESTONE-0008

#### Scope

- `ModelRegistry` and replaceable backend protocol.
- `FilesystemModelRegistry` with atomic Git-friendly YAML metadata and repository-local artifacts.
- Immutable `ModelManifest` and `TrainingProvenance`.
- Replaceable model artifact codecs.
- Independent calibration manifests/artifacts.
- Append-only benchmark observations and lifecycle events.
- CLI: `automo models list/show/compare/diff/history/active/archived`.

#### Non-goals

- Mandatory MLflow, S3, or database services.
- Dynamic model pools, automatic drift detection, automatic recalibration, or deployment.

#### Exit criteria

- [x] EC-001: Every registered model captures reconstructable model-spec, feature-set, objective, data-snapshot, runner, environment/code, and artifact lineage.
- [x] EC-002: The default filesystem registry is deterministic, human-inspectable, append-oriented, and keeps changing evidence separate from immutable model identity.
- [x] EC-003: Model artifacts are persisted and loaded through replaceable codecs rather than a hard-coded serialization format.
- [x] EC-004: Calibration artifacts are versioned independently and reference an existing base model without duplicating it.
- [x] EC-005: Repeated local/downstream/risk/operational benchmark evidence can be appended without rewriting model manifests.
- [x] EC-006: Lifecycle transitions are explicit, validated, append-only, and inspectable.
- [x] EC-007: `automo models list/show/compare/diff/history/active/archived` expose registry state without loading every model artifact.
- [x] EC-008: A custom registry backend can replace the filesystem backend without changing the research-runtime fitting API.

#### Evidence

- EC-001: `src/automo/registry/contracts.py`, `src/automo/runtime/project.py`, `tests/test_registry.py`.
- EC-002: `src/automo/registry/filesystem.py` and manifest-immutability benchmark tests.
- EC-003: `ModelArtifactCodec`, `LinearModelJsonCodec`, and load/hash verification tests.
- EC-004: `CalibrationManifest`, `register_calibration`, and independent-calibration test.
- EC-005: `BenchmarkObservation`, benchmark catalogue storage, and append-without-manifest-rewrite test.
- EC-006: `ModelStatus`, lifecycle event stream, legal-transition tests, and `models history`.
- EC-007: `src/automo/cli.py` model commands and CLI contract test.
- EC-008: replaceable custom-registry runtime test.

#### Next milestone

MILESTONE-0010

### MILESTONE-0010 — Model pool and data-iteration refresh lifecycle

- **Status:** completed
- **Outcome:** Automo maintains compatible model pools across immutable data iterations and evaluates recalibration/retraining through fit, validation, and refresh-OOS partitions without assuming datetime data.
- **Why now:** The registry can retain models; recurring data updates require reusable evaluation, recalibration, retention, and selection infrastructure before bounded automated research.
- **Depends on:** MILESTONE-0009

#### Scope

- Dataset-agnostic data iterations and split strategies.
- Training, calibration, retention, and selection policies.
- Fit → validation → refresh-OOS governance for fitted-state changes.
- Model-pool snapshots, scorecards, benchmark/lifecycle updates, and refresh history.
- Refresh and pool CLI.

#### Non-goals

- Open-ended AutoML, deployment, online learning, feature-distribution drift detection, or contextual bandits.

#### Exit criteria

- [x] EC-001: Data iterations require immutable snapshot identity but no datetime field.
- [x] EC-002: Predefined, hash/group, ordered, and temporal split protocols share one partition contract.
- [x] EC-003: Refresh candidates that change fitted state use fit → validation → refresh-OOS.
- [x] EC-004: Recalibration is fit on fit data, gated on validation, and tested only after freeze.
- [x] EC-005: Retraining creates a new model identity and is ranked only after validation freeze and refresh-OOS.
- [x] EC-006: Compatible models coexist in persisted model-pool snapshots.
- [x] EC-007: Training, calibration, retention, and selection are independent policies.
- [x] EC-008: Retention uses scorecards, minimum evidence/stability gates, and compatible primary metrics.
- [x] EC-009: Refresh reports, pool snapshots, benchmarks, calibrations, and model identities remain append-only or immutable.
- [x] EC-010: `automo refresh` and model-pool/history commands work on non-temporal ID data.

#### Evidence

- EC-001: `DataIteration` and ID-only ordered split test.
- EC-002: `PredefinedSplit`, `HashSplit`, `GroupSplit`, `OrderedSplit`, `TemporalSplit` and split tests.
- EC-003: `RefreshService.run` fit/validation/refresh-OOS flow and refresh tests.
- EC-004: recalibration validation-gate test and independent calibration artifact evidence.
- EC-005: retraining new-model-identity test and registry lineage.
- EC-006: `FilesystemPoolStore`, `ModelPoolSnapshot`, and pool-state tests.
- EC-007: training/calibration/retention/selection policy contracts and tests.
- EC-008: refresh scorecards, benchmark catalogue, minimum sample and stability gate tests.
- EC-009: refresh report/pool snapshot immutability plus append-only benchmark/lifecycle tests.
- EC-010: ID-only refresh/pool CLI integration test and `docs/refresh.md`.

#### Next milestone

MILESTONE-0011

### MILESTONE-0011 — Bounded automated research and interventions

- **Status:** completed
- **Outcome:** Automo generates reproducible baseline-plus-intervention candidates from structured evidence, enforces committed search budgets, progressively filters candidates through validation before bounded sealed research-OOS, records hypothesis exposure, and registers accepted fitted candidates without activating or deploying them.
- **Why now:** Model pools and refresh are stable; automated candidate generation can now build on reusable data, feature, fitting, registry, and refresh infrastructure without duplicating those concerns.
- **Depends on:** MILESTONE-0010

#### Scope

- First-class research interventions and declarative search spaces.
- Evidence-directed deterministic candidate generation.
- Candidate fingerprints/history and duplicate prevention.
- Research budgets and progressive validation → sealed research-OOS evaluation.
- Basic multiple-testing safeguards and exposure reporting.
- Bounded model, feature-set, parameter, and calibration interventions.
- Missing-capability requests and immutable model-registry handoff.
- `automo research plan/status/run/history/show/candidates` CLI.

#### Non-goals

- Unlimited AutoML, Bayesian HPO, neural architecture search, arbitrary feature synthesis, test-set-driven tuning, deployment, or unrestricted agent-generated experiments.

#### Exit criteria

- [x] EC-001: Candidates are persisted as a known baseline plus one explicit reproducible intervention.
- [x] EC-002: Plugins can declare bounded model, feature-set, calibration, and parameter research spaces.
- [x] EC-003: Structured diagnoses deterministically constrain and prioritize candidate generation.
- [x] EC-004: Candidate count, fit count, and sealed-OOS slots are committed and enforced before execution.
- [x] EC-005: Candidates pass validation selection before the bounded shortlist can access sealed research-OOS.
- [x] EC-006: Trial counts, minimum effect gates, observation gates, and repeated validation exposure are persisted.
- [x] EC-007: Equivalent prior candidate fingerprints are excluded from later research queues.
- [x] EC-008: Built-in bounded research executes model, feature-set, parameter, and calibration interventions.
- [x] EC-009: Accepted fitted candidates receive new immutable registry identities but are not automatically activated or deployed.
- [x] EC-010: Missing runners/calibrators persist bounded capability requests instead of failing opaquely.
- [x] EC-011: `automo research plan/status/run/history/show/candidates` operate end to end and are documented.

#### Evidence

- EC-001: `src/automo/research/contracts.py`, candidate-plan persistence, and explicit-intervention tests.
- EC-002: `ResearchSearchSpace`, `ResearchPlugin.research_spaces`, and plugin/CLI tests.
- EC-003: diagnosis transition rules in `src/automo/research/service.py` and evidence-directed planning tests.
- EC-004: `ResearchBudget` plus candidate/fit/OOS enforcement tests.
- EC-005: progressive validation shortlist and one-slot sealed-OOS test.
- EC-006: `ResearchSafeguards`, `ResearchIterationReport`, and trial/exposure evidence.
- EC-007: persisted candidate fingerprints and duplicate-research test.
- EC-008: model/feature/parameter/calibration intervention execution paths and research tests.
- EC-009: accepted-candidate registry test and no pool/deployment mutation.
- EC-010: capability request persistence from missing runtime capability.
- EC-011: `src/automo/cli.py`, CLI integration test, and `docs/research.md`.

#### Next milestone

None

### MILESTONE-0012 — Custom training and composable model graphs

- **Status:** completed
- **Outcome:** Automo supports generic custom fitting/evaluation and leakage-safe model graphs so downstream/meta-model research does not require users to rebuild research governance.
- **Why now:** Public release requires a training boundary broader than scalar supervised ML and safe support for models consuming other model outputs.
- **Depends on:** MILESTONE-0011

#### Scope

- Generic trainer/prediction/evaluation requests and structured outputs.
- Injected project services for external training/evaluation packages.
- Model DAG contracts and deterministic cross-fitting for upstream model outputs.
- Graph provenance and bounded graph research interventions.
- Synthetic onboarding examples and documentation.

#### Non-goals

- Domain-specific schemas, serving, deployment, arbitrary graph-depth cross-fitting, or internal-project examples.

#### Exit criteria

- [x] EC-001: Full custom trainer hook.
- [x] EC-002: Fit-partition isolation.
- [x] EC-003: Generic domain evaluator contract.
- [x] EC-004: Structured model outputs.
- [x] EC-005: Model dependency graphs.
- [x] EC-006: Leakage-safe cross-fitted meta training.
- [x] EC-007: Frozen graph validation/OOS evaluation.
- [x] EC-008: Graph provenance.
- [x] EC-009: Graph research interventions.
- [x] EC-010: External-service synthetic example.
- [x] EC-011: Runnable synthetic onboarding examples.

#### Evidence

- EC-001: `TrainingRequest`, `TrainingResult`, and custom trainer tests.
- EC-002: caller-scoped fit rows in runtime/graph tests.
- EC-003: `EvaluationContext`, `Evaluator`, and external-service evaluator test.
- EC-004: `ModelOutputBatch` and structured-output example.
- EC-005: `ModelGraphSpec`, `ModelNodeSpec`, `ModelOutputInput`, and graph tests.
- EC-006: deterministic cross-fit implementation and memorizing-upstream leakage test.
- EC-007: graph validation/OOS evaluation test using frozen fitted graph.
- EC-008: graph registry provenance test with upstream registered model IDs and cross-fit metadata.
- EC-009: `src/automo/research/graph.py` node-model/input intervention tests.
- EC-010: `examples/custom-trainer/example.py` external-service example.
- EC-011: `tests/test_examples.py` and all five synthetic onboarding examples.

#### Next milestone

None

### MILESTONE-0013 — Public alpha hardening

- **Status:** active
- **Outcome:** Automo `0.3.0a1` is publishable with clean packaging, versioned persistence, documented public APIs/security boundaries, runnable onboarding, and verified wheel/sdist installs.
- **Why now:** The reusable research architecture is complete enough for external use; remaining work is release quality and evidence rather than new research capability.
- **Depends on:** MILESTONE-0012

#### Scope

- Automo-only package/CLI identity and clean source tree.
- Versioned public persistence and one package-version source.
- Public API, trust-boundary, onboarding, and release documentation.
- Fresh project scaffolding and controlled CLI failures.
- Wheel/sdist clean-install release gates.
- Complete pre-commit repository-quality gate plus Python 3.11–3.13 CI.

#### Non-goals

- New research algorithms, deployment, distributed training, or domain-specific examples.

#### Exit criteria

- [x] EC-001: No legacy package/CLI identity ships.
- [x] EC-002: Generated runtime/build state is excluded from clean source/release artifacts.
- [x] EC-003: Version metadata has one source of truth.
- [x] EC-004: Public persisted artifacts carry artifact type/schema version metadata.
- [x] EC-005: Supported public extension imports are documented and tested.
- [x] EC-006: Trusted-code extension/model-artifact boundaries are documented.
- [x] EC-007: Fresh `automo init` projects validate and pass doctor.
- [x] EC-008: Seven synthetic onboarding examples run.
- [x] EC-009: Common CLI missing-ID failures are controlled and traceback-free.
- [x] EC-010: Wheel clean-install smoke passes.
- [x] EC-011: Sdist clean-install smoke passes.
- [ ] EC-012: Python 3.11–3.13 connected CI passes.
- [ ] EC-013: CI complete pre-commit hooks pass, including repository/configuration hygiene and Ruff lint/format.
- [x] EC-014: Public release docs and terminology are ready.

#### Evidence

- EC-001: `pyproject.toml`, wheel/sdist inspections, and no legacy package/CLI tests.
- EC-002: `MANIFEST.in`, `.gitignore`, `scripts/source_check.py`, and release artifact inspection.
- EC-003: `src/automo/_version.py` and dynamic setuptools version metadata.
- EC-004: `src/automo/persistence/` plus schema persistence tests.
- EC-005: `src/automo/__init__.py`, `docs/public-api.md`, and public API tests.
- EC-006: `SECURITY.md` and `docs/release-contract.md`.
- EC-007: fresh init/validate/doctor public release test and wheel/sdist smoke.
- EC-008: `tests/test_examples.py` and seven synthetic example directories.
- EC-009: common missing-ID controlled CLI error test.
- EC-010: wheel clean-install branch of `scripts/health_gate.py`.
- EC-011: sdist clean-install branch of `scripts/health_gate.py`.
- EC-012: `.github/workflows/ci.yml`; connected execution evidence pending.
- EC-013: `.pre-commit-config.yaml` and CI invocation; connected execution evidence pending.
- EC-014: README, CHANGELOG, ROADMAP, security, getting-started, public API, and release-contract docs.

#### Next milestone

none

### MILESTONE-0014 — Agent research guidance and governance

- **Status:** completed
- **Outcome:** Automo supplies deterministic agent-facing research guidance, `.automo/` milestone/plan-mode governance, and a bounded optional GetDone development handoff without sharing state ownership.
- **Why now:** Public-alpha review exposed that the deterministic research engine lacked the agent reasoning/governance layer required for autonomous but bounded research.
- **Depends on:** MILESTONE-0012

#### Scope

- Packaged workflows, standards, acceptance gates, policies, references, and handoff contract for research agents.
- `automo guidance` task-specific minimal selection.
- `.automo/` research project, roadmap, current plan, milestone, and next-step state.
- Research milestone lifecycle with plan mode and active execution guard.
- Capability requests/results/handoffs under `.automo/capabilities/` with `.agent/` reserved for GetDone.

#### Non-goals

- New model algorithms, broader search methods, automatic GetDone project mutation, deployment, or domain-specific research rules.

#### Exit criteria

- [x] EC-001: Fresh init creates `.automo/` research governance in plan mode.
- [x] EC-002: Milestones follow proposed → planning → approved → active → concluded with accepted/rejected/inconclusive/invalid outcomes.
- [x] EC-003: Governed automated research refuses execution outside an active milestone.
- [x] EC-004: `automo guidance` emits a minimal task-specific installed research guidance set.
- [x] EC-005: Guidance covers experiment design, diagnosis, features, calibration, meta-model leakage, refresh, conclusion, and capability handoff.
- [x] EC-006: Capability requests/results/handoffs live under `.automo/`; GetDone development state remains `.agent/`.
- [x] EC-007: GetDone handoff is explicit, bounded, and does not cause Automo to write `.agent/`.
- [x] EC-008: Human docs explain governance, guidance, and GetDone composition.
- [x] EC-009: Full regression and installed-wheel guidance checks pass.

#### Evidence

- EC-001: `src/automo/governance.py` init contract and `test_init_creates_automo_research_governance`.
- EC-002: milestone transition/outcome contracts and `test_milestone_lifecycle_and_plan_mode`.
- EC-003: `ResearchGovernance.require_execution_ready` and plan-mode guard test.
- EC-004: `src/automo/guidance.py`, packaged `src/automo/skill/`, and guidance CLI tests.
- EC-005: workflow/standard/policy/reference files under `src/automo/skill/`.
- EC-006: `.automo/capabilities/` request/result paths in research/capability services.
- EC-007: `create_getdone_handoff`, `automo capability handoff`, and ownership test.
- EC-008: `docs/research-governance.md`, `docs/agent-guidance.md`, README, getting-started, and release contract.
- EC-009: `python -m pytest -q` reported 102 passed; installed-wheel guidance smoke emitted the expected meta-model guidance paths.

#### Next milestone

MILESTONE-0013

### MILESTONE-0015 — Research guidance completeness and agent safety

- **Status:** completed
- **Outcome:** Automo's first-alpha agent guidance includes bounded diagnosis, multiple-testing/selection-bias handling, early stopping, meta-model ablation/OOF rules, refresh decisions, adherence gates, and executable validation.
- **Why now:** Pre-alpha review concluded the M14 guidance architecture needed deeper methodology and agent-reliability checks before publication.
- **Depends on:** MILESTONE-0014

#### Scope

- Diagnosis and intervention-selection guidance.
- Multiple-testing/selection-bias and early-stopping policies.
- Meta-model incremental-value/ablation safety.
- Refresh-vs-research guidance and inconclusive outcomes.
- Guidance-pack validation, CLI drift tests, and sequential walkthrough.

#### Non-goals

- New algorithms, domain-specific statistical guarantees, or broader automated search.

#### Exit criteria

- [x] EC-001: Every task class resolves to bounded valid guidance.
- [x] EC-002: Multiple testing/selection bias is explicit.
- [x] EC-003: Early stopping/diminishing returns is explicit.
- [x] EC-004: Common diagnosis failure modes are covered.
- [x] EC-005: Meta-model OOF/ablation/incremental-value rules are covered.
- [x] EC-006: Refresh/lifecycle action is distinguished from new research.
- [x] EC-007: Negative agent-adherence scenarios are explicit.
- [x] EC-008: Documented CLI paths are tested.
- [x] EC-009: Multi-milestone synthetic walkthrough passes.
- [x] EC-010: Full local regression passes (110 tests).

#### Evidence

- EC-001: `validate_guidance_pack` and task-class coverage tests.
- EC-002: `skill/policies/multiple-testing.md` and high-risk task routing tests.
- EC-003: `skill/policies/early-stopping.md` and milestone/experiment workflow coverage.
- EC-004: `skill/standards/diagnosis.md`, diagnosis patterns, and intervention decision table.
- EC-005: expanded meta-model workflow/reference plus leakage guidance selection tests.
- EC-006: expanded refresh-analysis workflow and intervention decision table.
- EC-007: `skill/acceptance/agent-adherence.md` and failure-mode coverage test.
- EC-008: documented command existence test against the Typer CLI tree.
- EC-009: `examples/research-guidance/` walkthrough and executable example test.
- EC-010: `python -m pytest -q` reported 110 passed.

#### Next milestone

MILESTONE-0013

## Deferred work

- Public model-source discovery — reconsider after local lifecycle infrastructure is mature.
- Automated production deployment — remains out of scope until separately planned.



### MILESTONE-0016 — Consumer compatibility and project-agent composition hardening

- **Status:** completed
- **Outcome:** Project-owned `.project-agent/` research rules compose deterministically with Automo guidance, extension contracts support thin domain adapters, and a real xihbm compatibility fixture was checked.
- **Why now:** User-approved pre-alpha hardening before release CI.
- **Depends on:** MILESTONE-0015

#### Exit criteria

- [x] EC-001: Project-agent composition, locking, and validation are operational.
- [x] EC-002: Provenance/pool/selector/calibration extension contracts are generalized.
- [x] EC-003: Research-plan conformance and state-schema checks are enforced.
- [x] EC-004: xihbm compatibility boundary is demonstrated with relevant tests.

#### Evidence

- `tests/test_m16_compatibility.py`, 119-test full regression, 19-test xihbm compatibility subset, and GetDone 1.1.2 project validation.

#### Next milestone

MILESTONE-0013 resumes for connected CI/pre-commit release evidence.
