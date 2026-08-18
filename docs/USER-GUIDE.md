# Automo User Guide

Automo separates reusable research governance from project-specific model logic. A project supplies data sources, features, models, trainers, evaluators, and optional external services; Automo owns partitions, evidence boundaries, lineage, refresh, bounded research, and model lifecycle records.

## Installation

```bash
python -m pip install automo
automo --version
```

Optional GetDone integration is installed separately:

```bash
python -m pip install "automo[getdone]"
automo integration status
```

GetDone is not required for normal Automo use.

## Create a project

```bash
automo init --root my-project
cd my-project
automo validate
automo doctor
```

The generated project includes:

```text
automo.toml
automo_project.py
research/
data/
README.md
```

`automo_project.py` contains an initially empty but valid `ResearchPlugin`. Populate it with the components your project needs.

## Extension boundary

A typical project plugin may contribute:

```python
ResearchPlugin(
    id="project",
    data_sources=(...),
    feature_computers=(...),
    feature_sets=(...),
    objectives=(...),
    metrics=(...),
    model_specs=(...),
    model_runners=(...),
    model_trainers=(...),
    evaluators=(...),
    model_graphs=(...),
    services={...},
)
```

Use a `ModelTrainer` when fitting must call an external package, needs multiple inputs, or does not fit the ordinary `rows + numeric target` shape. Trainers receive only the committed fit partition; Automo retains control of validation and OOS evidence.

## Data partitioning

Datetime is optional. Choose partition semantics that match the data:

- predefined partitions;
- stable hash splits;
- grouped splits;
- ordered-field/ID splits;
- temporal splits.

Refresh and research use the same partition contracts.

## Model graphs and meta-models

A node may consume ordinary features/data or `ModelOutputInput` values from upstream nodes. For fit-time downstream inputs, Automo cross-fits eligible upstream models and supplies out-of-fold predictions to the downstream trainer.

This supports leakage-safe first-level stacking such as:

```text
base A ─┐
        ├→ downstream model
base B ─┘
```

See `trainers-and-graphs.md` for graph provenance and current depth limitations.

## Model registry

Registered fitted models have immutable identity documents, artifact hashes, training provenance, benchmark history, calibration lineage, and explicit lifecycle events.

```bash
automo models list
automo models show MODEL-000001
automo models history MODEL-000001
```

See `model-registry.md`.

## Refresh lifecycle

A model pool can retain several compatible models. Each data iteration can evaluate existing models and, according to explicit policies, recalibrate or retrain them.

Whenever fitted state changes, refresh follows:

```text
fit → validation → freeze candidate → refresh-OOS → retention/selection
```

Recalibration creates a new calibration identity; retraining creates a new model identity. Existing artifacts are not overwritten.

```bash
automo refresh --help
automo refresh history
automo models pool <pool-id>
```

See `refresh.md`.

## Bounded automated research

Automo can generate explicit baseline-plus-intervention candidates from a declared search space and structured diagnosis. Budgets limit validation trials, model fits, and sealed research-OOS exposure.

```bash
automo research plan --help
automo research run --help
automo research history
```

Accepted research candidates may be registered, but are not automatically activated or deployed. See `research.md`.

## High-level deterministic experiment commands

The earlier committed-experiment workflow remains available for explicit deterministic research specifications:

```bash
automo status
automo plan
automo run
automo validate
```

Advanced stages are grouped under commands including `automo experiment`, `automo features`, `automo findings`, `automo stability`, `automo promotion`, and `automo capability`.

## Artifacts and compatibility

Public registry, refresh, pool, and bounded-research artifacts written by `0.3.0a2` contain:

```yaml
artifact_type: automo.example
schema_version: 1
```

Automo treats these schemas as current contracts. Incompatible persisted state is rejected rather than migrated implicitly. The alpha Python API can still evolve; use the contracts documented in `public-api.md` rather than concrete filesystem service classes where possible.

## Troubleshooting

Start with:

```bash
automo validate
automo doctor
```

Normal configuration/plugin errors should be reported without a traceback. For extension-code failures, debug the project trainer/evaluator/service directly; those extensions run as trusted Python code and are not sandboxed.

## Learn from examples

All onboarding examples are synthetic and domain-neutral:

```text
examples/basic-supervised
examples/custom-trainer
examples/meta-model
examples/structured-output
examples/id-only-data
examples/end-to-end
```

Each example contains a short README, a run command, expected output, and a next-document pointer.
