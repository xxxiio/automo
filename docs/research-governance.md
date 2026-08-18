# Research program governance

Automo owns mutable scientific research state under `.automo/`. GetDone, when used for project delivery and software development, owns project direction, roadmap/milestones, and `.agent/`. Automo must not duplicate those milestones as scientific state.

A fresh `automo init` creates the scientific skeleton:

```text
.automo/
├── project.yaml
└── research-program/
    ├── program.yaml
    ├── model-graph.yaml
    ├── hypotheses/
    ├── candidates/
    └── composition-experiments/
```

Registry, research-run, pool, refresh, and capability state also live below `.automo/` as they are created.

## Two separate graphs

Automo deliberately separates system structure from scientific claims.

The **model graph** describes computation/information structure. Models may be independent, composed as submodel → meta-model inputs, or related only by correlation/complementarity.

The **hypothesis graph** describes falsifiable scientific claims. A hypothesis may be scoped to one primary model, reference related models, or test cross-model/system composition. It is not required to mirror the model graph.

Example:

```bash
automo research model-add ranking --role submodel
automo research model-add market --role submodel
automo research model-add meta --role meta
automo research model-relation-add ranking meta --kind input
automo research model-relation-add market meta --kind input
```

A flat informational relation can be represented without creating an execution dependency:

```bash
automo research model-relation-add ranking market --kind correlated
```

## Model candidates and exact composition

A `ModelComponent` is the logical role in the system; a model candidate is one immutable researched version of that component. Candidate records pin the `model_spec_id`, point at the runtime/registry artifact, and, for composed models, pin the exact upstream candidate versions used to construct it.

```bash
automo research candidate-add RANK-v1 \
  --model ranking \
  --model-spec-id ranking-v1 \
  --artifact-id MODEL-RANK-v1

automo research candidate-add MARKET-v2 \
  --model market \
  --model-spec-id market-v2 \
  --artifact-id MODEL-MARKET-v2

automo research candidate-add META-market-v3 \
  --model meta \
  --model-spec-id meta-linear \
  --artifact-id MODEL-META-market-v3 \
  --input market:MARKET-v2

automo research candidate-add META-market-rank-v3 \
  --model meta \
  --model-spec-id meta-linear \
  --artifact-id MODEL-META-market-rank-v3 \
  --input ranking:RANK-v1 \
  --input market:MARKET-v2

automo research candidate-select META-market-rank-v3
```

Selection is per logical model. Selecting a new candidate replaces the previous selected candidate for that model but does not delete historical candidates or evidence.

## Composition and ablation experiments

A composition experiment asks whether a different composition or target-model specification adds value while holding the committed comparison dimensions explicit. Automo rejects experiments that change both dimensions at once. This supports two common designs:

1. **Incremental-input ablation:** compare two immutable target-model candidates that differ only by one pinned upstream input.
2. **Composition-algorithm comparison:** compare two target-model candidates that pin the same upstream inputs but use different target-model artifacts/implementations.

For an input ablation:

```bash
automo research hypothesis-create H-RANK-INCREMENTAL \
  --statement "Ranking adds incremental information beyond market." \
  --primary-model meta \
  --related-model ranking \
  --objective log_loss:parent:minimize \
  --evaluation-depth parent

automo research composition-create EXP-RANK-ABLATION \
  --hypothesis H-RANK-INCREMENTAL \
  --target-model meta \
  --control-candidate META-market-v3 \
  --treatment-candidate META-market-rank-v3 \
  --metric log_loss \
  --metric brier \
  --rationale "Isolate ranking's incremental contribution." \
  --expected-effect "Improve OOS probability quality without calibration degradation." \
  --falsification "No committed metric improves materially."
```

Automo validates candidate composition at candidate-registration time: every pinned input candidate must belong to the named upstream model, and an `input` relation must exist from that upstream model to the target model. A composition experiment then compares two distinct immutable candidates of the same target model. Correlated/complementary/alternative relations describe information structure but do not authorize runtime composition.

The model graph and candidate graph therefore answer different questions: the model graph says which logical components may interact; candidate records say exactly which researched versions were used; composition experiments say which controlled comparison produced the evidence.

## Hypothesis lifecycle

Create a root claim and child claims as needed:

```bash
automo research hypothesis-create H-ROOT \
  --statement "The system provides useful out-of-sample predictive value." \
  --primary-model meta \
  --evaluation-depth system

automo research hypothesis-create H-RANK \
  --parent H-ROOT \
  --statement "Ranking provides incremental predictive information." \
  --primary-model ranking \
  --related-model meta \
  --evaluation-depth parent
```

Activate the immediate scientific context before governed automated research:

```bash
automo research hypothesis-activate H-RANK
```

After evidence is sufficient:

```bash
automo research hypothesis-conclude H-RANK \
  --status supported \
  --conclusion "Parent-level evaluation shows incremental value."
```

Valid conclusion states are `supported`, `rejected`, and `inconclusive`. A local improvement is not sufficient when the hypothesis requires parent or system evidence.

## GetDone boundary

GetDone/project roadmap material answers **what direction matters next**. Automo answers **what scientific claims are unresolved and what evidence is needed**. Automo may consume project direction as prioritization context but does not persist milestone lifecycle state.

When research requires missing software capability, Automo persists a bounded capability request under `.automo/capabilities/requests/` with program/hypothesis/experiment provenance. Optional GetDone delegation may implement that capability, using `.agent/` for development workflow state. Automo protects research evidence from delegated mutation and independently validates the returned implementation result before research resumes.
