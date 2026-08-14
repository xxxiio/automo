# Model pools and refresh

Automo separates **research** (inventing new candidates) from **refresh** (operating already-known model families against a new immutable data snapshot).

## Data does not need a datetime

Refresh works through explicit split strategies. A project may use:

- `PredefinedSplit` for supplied row partitions;
- `HashSplit` for deterministic IID assignment using any stable key;
- `GroupSplit` to keep related observations together;
- `OrderedSplit` for monotonically meaningful IDs or sequence fields;
- `TemporalSplit` when a timestamp really is the correct ordering semantic.

A `DataIteration` records the immutable snapshot identity. `created_at` is workflow metadata; no datetime column is required in the dataset.

## Fit, validation and refresh-OOS

Whenever refresh changes fitted state, it follows the same governance boundary as research:

1. Fit or recalibrate only on the **fit** partition.
2. Compare the candidate variant on **validation**.
3. Freeze the winning variant.
4. Evaluate that frozen variant on **refresh-OOS**.
5. Rank/retain models only from governed scorecards.

A recalibration that fails validation never sees refresh-OOS as a candidate variant. Retraining always creates a new model identity; it never overwrites an existing registry artifact.

## Thin project configuration

A plugin can register model pools, calibrators and split strategies alongside its existing data/features/models:

```python
ResearchPlugin(
    ...,
    model_pools=(pool,),
    calibrators=(AffineCalibrator(),),
    split_strategies=(OrderedSplit("id"),),
)
```

Run a dry plan:

```bash
automo refresh \
  --pool ranking \
  --data-source latest \
  --split ordered \
  --iteration ITER-2026-08-14 \
  --dry-run
```

Execute it:

```bash
automo refresh \
  --pool ranking \
  --data-source latest \
  --split ordered \
  --iteration ITER-2026-08-14
```

Inspect history:

```bash
automo refresh history
automo refresh show ITER-2026-08-14
automo models pool ranking
automo models pool-history ranking
```

Refresh reports and pool snapshots are immutable per iteration.
