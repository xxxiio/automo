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

## Define the first research hypothesis

A fresh project has no active scientific claim. Define the relevant model structure and a falsifiable hypothesis before governed automated research:

```bash
automo research model-add baseline --role standalone
automo guidance --task-class hypothesis-planning
automo research hypothesis-create H-ROOT \
  --statement "The system provides useful out-of-sample predictive value." \
  --primary-model baseline \
  --evaluation-depth system
automo research hypothesis-activate H-ROOT

# Once a trained artifact exists, register it as a logical model candidate.
automo research candidate-add BASE-v1 --model baseline --model-spec-id baseline-v1 --artifact-id MODEL-BASE-v1
automo research candidate-select BASE-v1
```

Project roadmap and milestone direction should remain in GetDone or the project's own planning system. See [Research governance](research-governance.md) and [Agent guidance](agent-guidance.md).

## Project-specific research guidance

Keep mutable research state under `.automo/` and project-owned agent instructions under `.project-agent/automo/`. `automo guidance` discovers `.project-agent/automo/index.json` additively by default; use `--no-project-agent` for canonical Automo-only guidance. Pin a reviewed composition with `automo guidance-lock --write` and verify it with `automo guidance-check`. Project guidance may strengthen or specialize research rules but cannot replace protected sealed-OOS, bounded-search, evidence, or hypothesis-governance rules.
