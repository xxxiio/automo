# Public Python API

Automo `0.3.0a2` is an alpha. The package distinguishes stable extension surfaces from implementation details so external projects do not need to depend on filesystem services or orchestration internals.

## Root-level public contracts

The following are intentionally importable from `automo`:

- data: `DataSource`, `DataSnapshot`, `DataInput`;
- features: `FeatureSpec`, `FeatureSetSpec`, `FeatureComputer`, `FeatureSetInput`;
- objectives/evaluation: `ObjectiveSpec`, `MetricSpec`, `MetricDirection`, `MetricScope`, `EvaluationSpec`, `EvaluationContext`, `Evaluator`;
- models: `ModelSpec`, `ModelTrainer`, `TrainingRequest`, `TrainingResult`, `ModelOutputBatch`;
- graphs: `ModelGraphSpec`, `ModelNodeSpec`, `ModelOutputInput`, `CrossFitSpec`;
- plugin/runtime: `ResearchPlugin`, `ResearchRuntime`;
- research governance: `ResearchGovernance`, `ResearchHypothesis`, `ResearchProvenance`, `ModelComponent`, `ModelRelation`, `ModelCandidate`, `CandidateInput`, `CompositionExperiment`, `HypothesisObjective`, `EvaluationDepth`.

These contracts are the preferred extension boundary for project packages.

## Subpackage public contracts

Some lifecycle abstractions are intentionally namespaced:

```python
from automo.registry import ModelRegistry, ModelStatus
from automo.refresh import ModelPoolSpec, SplitStrategy
from automo.research import ResearchSearchSpace, ResearchBudget
```

## Experimental/internal modules

Filesystem stores, orchestration services, local execution helpers, and modules named `service`, `local`, or similar are implementation details unless explicitly documented otherwise. External packages should not rely on their concrete file layout during the alpha series.

## Compatibility policy

Persistent public artifacts have explicit `artifact_type` and `schema_version` fields. Python APIs may still evolve during `0.3.0aN`, but changes to the documented extension contracts should be deliberate and recorded in the changelog.
