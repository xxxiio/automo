# Bounded automated research

Automo separates **research** from **refresh**. Refresh operates known models as new data arrives; research proposes and evaluates bounded new candidates.

## Core rule

Every candidate is a known baseline plus an explicit intervention. Automo records the intervention fingerprint, rationale, trial counts, validation evidence, and sealed research-OOS evidence.

Supported built-in intervention categories in this release are:

- model choice (`model`)
- feature-set replacement (`feature_set`)
- bounded parameter changes (`parameters`)
- calibration (`calibration`)

The contracts also reserve explicit kinds for feature additions/removals and training-window changes so downstream generators can extend the system without opaque configuration blobs.

## Thin plugin configuration

A project can register a `ResearchSearchSpace` through `ResearchPlugin.research_spaces`:

```python
ResearchSearchSpace(
    id="default",
    model_spec_ids=("linear", "lightgbm-small"),
    feature_set_ids=("core", "core-plus-regime"),
    calibrator_ids=("affine",),
    parameter_choices={"max_depth": (3, 5, 7)},
)
```

This describes the **legal** space. Automo does not blindly enumerate its Cartesian product.

## Evidence-directed planning

A structured diagnosis narrows candidate types. For example:

- `poor_calibration` → calibration candidates
- `underfitting` → model / feature-set / parameter candidates
- `overfitting` → parameter / feature-set candidates
- `feature_gap` → feature-set candidates

Each proposal persists rationale, expected effect, and falsification criteria.

## Workflow

```bash
automo research plan RESEARCH-0001 \
  --baseline baseline-model \
  --data-source training-data \
  --split predefined \
  --space default \
  --diagnosis underfitting \
  --maximum-candidates 8 \
  --maximum-oos-candidates 2 \
  --minimum-improvement 0.003

automo research candidates RESEARCH-0001
automo research status RESEARCH-0001
automo research run RESEARCH-0001 --space default
automo research show RESEARCH-0001
automo research history
```

## Progressive evaluation

Automo fits candidates on the committed fit partition and evaluates all eligible candidates on validation. Only the bounded validation shortlist is allowed to touch sealed research-OOS.

Trial counts are written to the final report:

- proposals generated
- validation trials performed
- sealed OOS trials performed
- repeated validation exposure

Accepted fitted candidates are registered as new immutable model identities. They become eligible for later model-pool admission; research does not silently activate or deploy them.

## Duplicate protection

Candidate fingerprints include the baseline plus the explicit intervention. A previously proposed equivalent candidate is rejected from a new research queue rather than consuming another trial silently.

## Missing capabilities

If a candidate requires a runner or calibrator that is not registered, Automo persists a bounded capability request under `.automo/capabilities/requests/`. Optional GetDone delegation can then implement the missing capability through the existing governed capability workflow.

## Statistical boundary

Validation is adaptive research evidence. Sealed research-OOS is touched only by the bounded shortlist after validation selection. Refresh-OOS remains a different evidence class used for recurring operational refresh.


## Logical model candidates versus bounded search candidates

The bounded-research engine uses `CandidateProposal` for one baseline-plus-intervention trial inside a research plan. Research governance separately uses immutable logical **model candidates** to identify retained versions of a model component such as `ranking`, `market`, or `meta`.

Use `automo research candidate-add` when a trained/registered artifact should become a named candidate in the research program. Use `automo research composition-create` when the scientific question is incremental contribution, ablation, or composition architecture rather than a local single-model intervention. See [Research governance](research-governance.md).
