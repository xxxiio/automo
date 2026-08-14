# Getting started

This walkthrough uses a minimal synthetic project and does not require timestamps, external infrastructure, or GetDone.

## 1. Initialize

```bash
automo init --root demo
cd demo
automo validate
automo doctor
```

The generated project contains `automo.toml` and `automo_project.py`. The initial plugin is intentionally empty but valid.

## 2. Choose the smallest example that matches your use case

For ordinary tabular fitting:

```bash
python ../examples/basic-supervised/example.py
```

For a custom training package or service:

```bash
python ../examples/custom-trainer/example.py
```

For stacking/meta-models:

```bash
python ../examples/meta-model/example.py
```

For data with IDs but no datetime column:

```bash
python ../examples/id-only-data/example.py
```

## 3. Build the project plugin

A project plugin contributes domain-specific objects while Automo owns the surrounding lifecycle:

```python
from automo import ResearchPlugin


def create_plugin() -> ResearchPlugin:
    return ResearchPlugin(
        id="my-project",
        data_sources=(...),
        feature_computers=(...),
        feature_sets=(...),
        objectives=(...),
        metrics=(...),
        model_specs=(...),
        model_runners=(...),
        model_trainers=(...),
        evaluators=(...),
        services={...},
    )
```

Use `ModelTrainer` when fitting needs full control or an external package. Use `ModelOutputInput` in a `ModelGraphSpec` when a model consumes another model's output.

## 4. Validate before research

```bash
automo validate
automo doctor
```

Then use the workflow that matches the task:

```bash
automo research --help
automo refresh --help
automo models --help
```

Read `trainers-and-graphs.md` before implementing a downstream/meta-model so the cross-fitting boundary is clear.
