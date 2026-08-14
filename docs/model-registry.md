# Model registry and lifecycle

Automo's model registry keeps fitted model identity separate from evidence that changes over time.
This makes it possible to retain, inspect, recalibrate, and compare models without rewriting the
record that explains how a base estimator was created.

## Default filesystem registry

The built-in registry is `FilesystemModelRegistry`. A project can use it at `.automo/registry`:

```python
from pathlib import Path

from automo.registry import FilesystemModelRegistry

registry = FilesystemModelRegistry(Path(".automo/registry"))
```

The layout is human-inspectable and Git-friendly:

```text
.automo/registry/
├── models/
│   └── MODEL-000001/
│       ├── manifest.yaml
│       ├── provenance.yaml
│       └── artifact/model.bin
├── calibrations/
├── benchmarks/
└── events/
```

Model manifests and training provenance are immutable identity records. Benchmarks, calibrations,
and lifecycle events are stored separately and appended over time.

## Fit and register

A model runner can expose an artifact codec. The standard runtime then handles feature
materialization, fitting, provenance capture, and registration:

```python
manifest = runtime.fit_and_register(
    "my-model-spec",
    data_source_id="train",
    registry=registry,
    seed=42,
)
```

Training provenance records the data source and snapshot, snapshot hash, feature set, model spec,
objective, runner implementation, Python version, seed, and code revision when available.

Plain `runtime.fit()` remains available when persistence is not wanted.

## Repeated evaluation

Benchmark history does not mutate the model manifest:

```python
model = registry.load_model(manifest.id)
runtime.evaluate_and_record(
    "my-model-spec",
    model,
    data_source_id="validation",
    registry=registry,
    registered_model_id=manifest.id,
    split="validation",
)
```

Benchmark observations carry metric direction and scope so local, downstream, risk, and
operational evidence can coexist without being treated as one global leaderboard.

## Independent calibration lineage

Calibration artifacts reference a base model rather than duplicating it. This allows future data
iterations to recalibrate a retained estimator independently from base-model training.

Automo 0.2 currently provides the registry contract for calibration artifacts; automatic
recalibration policy belongs to the later refresh lifecycle.

## Lifecycle

Registered models begin as `candidate`. The initial lifecycle states are:

```text
candidate → validated → active → degraded → archived
    └──────→ rejected
```

Only explicit legal transitions are accepted. Every transition is persisted as an append-only
lifecycle event with a timestamp and reason.

## CLI inspection

```bash
automo models list
automo models list --status active
automo models show MODEL-000001
automo models compare MODEL-000001 MODEL-000002
automo models diff MODEL-000001 MODEL-000002
automo models history MODEL-000001
automo models active
automo models archived
```

`compare` rejects models with different objectives rather than presenting a misleading ranking.
`diff` focuses on changes to implementation and provenance, while `history` shows lifecycle events.

## Replaceable backend

The runtime accepts the `ModelRegistry` protocol rather than depending on the filesystem backend.
A user package can therefore provide another registry implementation without replacing feature
computation, model fitting, evaluation, or the high-level research workflow.

Automo does not require MLflow, S3, or a database.
