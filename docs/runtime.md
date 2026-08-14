# Extensible research runtime

Automo supplies complete default infrastructure while keeping subsystem boundaries narrow.
A project can therefore start with a thin plugin and replace only the pieces that are genuinely
domain-specific.

## Thin plugin contract

A `ResearchPlugin` registers:

- data sources;
- feature computers and feature sets;
- objectives;
- metrics;
- model specifications;
- model runners.

Automo's `ResearchRuntime` resolves those registrations, materializes feature dependencies,
fits the requested model runner, and evaluates the model using the declared metrics.

```python
from automo.runtime import ResearchPlugin, ResearchRuntime

plugin = ResearchPlugin(
    id="my-project",
    data_sources=(...),
    feature_computers=(...),
    feature_sets=(...),
    objectives=(...),
    metrics=(...),
    model_specs=(...),
    model_runners=(...),
)

runtime = ResearchRuntime(plugin)
model = runtime.fit("candidate-v1", data_source_id="training")
metrics = runtime.evaluate("candidate-v1", model, data_source_id="validation")
```

## Project plugin discovery

A host package may expose a factory directly in `automo.toml`:

```toml
[project]
plugin = "my_package.automo:create_plugin"
```

or through the `automo.plugins` Python entry-point group:

```toml
[project]
plugin = "entrypoint:my-package"
```

This keeps project integration thin: the project defines domain data/features/objectives and
optional custom runners, while Automo owns the surrounding research runtime.

## Design principles

The runtime keeps the reusable research layer domain-neutral:

- immutable declarative model and feature specifications;
- feature selection independent from estimator implementation;
- explicit metric direction and evidence scope;
- optional ordering/availability semantics rather than mandatory timestamps;
- stable IDs suitable for registry and provenance lineage.
