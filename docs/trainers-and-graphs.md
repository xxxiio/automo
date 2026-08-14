# Custom trainers and composable model graphs

Automo owns research governance: immutable data partitions, fit/validation/OOS boundaries,
research budgets, evidence, model registry, refresh, and lifecycle history. A project owns only
the domain-specific pieces it actually needs.

## Custom training

Use `ModelTrainer` when fitting is more complicated than `X -> estimator.fit(y)`. A trainer
receives a `TrainingRequest` containing only the committed fit rows, resolved inputs, objective,
services, seed, and partition identity. It returns a `TrainingResult` with a predictor and optional
artifacts/metadata.

This allows a trainer to call another Python package, perform custom joins, use grouped/ranking
labels, fit several internal objects, or consume domain services without moving split governance
out of Automo.

```python
class ExternalTrainer:
    implementation = "demo.external"

    def fit(self, request: TrainingRequest) -> TrainingResult:
        engine = request.services["trainer"]
        predictor = engine.fit(request.rows, request.inputs)
        return TrainingResult(predictor=predictor)
```

A custom trainer never receives validation or sealed OOS rows through the training request.

## Generic outputs and evaluators

Predictors may return structured values through `ModelOutputBatch`; outputs do not need to be a
single float. A project can register an `Evaluator` that receives an `EvaluationContext` containing
the partition rows, model outputs, resolved inputs, objective, and injected services.

This supports outputs such as classes, distributions, actions, portfolios, or arbitrary immutable
Python values. Automo does not interpret those values; the registered evaluator does.

## Model graphs

`ModelGraphSpec` defines a DAG of model nodes. A node can consume feature sets, raw data, or output
from another node through `ModelOutputInput`.

```python
ModelGraphSpec(
    id="stack",
    nodes=(
        ModelNodeSpec("base_a", "base-a"),
        ModelNodeSpec("base_b", "base-b"),
        ModelNodeSpec(
            "meta",
            "meta",
            inputs=(
                ModelOutputInput("base_a", alias="a"),
                ModelOutputInput("base_b", alias="b"),
            ),
        ),
    ),
    output_node_id="meta",
)
```

## Leakage-safe meta-model fitting

For the fit partition, upstream outputs consumed by a downstream node are cross-fitted. Each
upstream fold is trained without its holdout rows and predicts only those held-out rows. The
resulting out-of-fold outputs become the meta-model's fit inputs.

Validation and OOS use the frozen full-fit upstream predictors and the frozen downstream predictor.
This prevents the common stacking leak where a meta-model is trained on upstream in-sample
predictions.

`CrossFitSpec` supports deterministic fold assignment and an optional stable key, so datasets do not
need datetime columns.

## Graph provenance

`GraphRuntime.register_graph()` registers graph nodes through the normal model registry. Training
provenance records the graph id, registered upstream model identities, and cross-fitting protocol.
Calibration remains separate from base-model identity.

## Researching graph structure

Automo research interventions can change a node's model specification or add/remove an upstream
model-output input. This makes model topology research an explicit, auditable intervention rather
than an opaque code change.

See `examples/custom-trainer`, `examples/meta-model`, and `examples/structured-output`.
