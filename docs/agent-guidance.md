# Agent research guidance

Automo ships a read-only research guidance pack inside the Python distribution. It plays the same role for model research that GetDone guidance plays for software development: an agent loads only the operational material needed for the current task instead of reading every document.

Use:

```bash
automo guidance --task-class milestone-planning
automo guidance --task-class experiment-design
automo guidance --task-class model-diagnosis
automo guidance --task-class meta-model-research
automo guidance --task-class milestone-conclusion
```

Use `--paths-only` when an agent or wrapper wants the selected package resources without their content. Available task classes are listed by `automo research task-classes`.

## Guidance architecture

The guidance pack separates workflows, standards, acceptance gates, policies, references, and contracts. Core research guidance is always included; specialist material is selected only when its task class applies. The selector is bounded and validated so one task does not pull the entire pack into agent context.

The guidance is procedure; `.automo/` is authoritative project-owned research state. An agent must inspect the current milestone and next step before governed execution.

## Governed research lifecycle

A normal sequence is:

1. enter plan mode and select the highest-value unresolved research question;
2. precommit milestone exit criteria, non-goals, data/split boundaries, candidate/OOS budgets, materiality, and stop rules;
3. approve and activate the milestone;
4. design one falsifiable intervention tied to the diagnosis;
5. execute without using sealed OOS for candidate generation;
6. record every attempted candidate and preserve failed evidence;
7. diagnose evidence before selecting the next intervention;
8. conclude `accepted`, `rejected`, `inconclusive`, or `invalid`;
9. return to plan mode with exactly one next step.

## Pre-alpha research safeguards

The pack includes explicit guidance for:

- **selection bias and multiple testing:** account for every attempted candidate, fix search breadth before execution, and raise the evidence bar as adaptive selection grows;
- **early stopping:** budgets are maxima, not quotas; stop when a hypothesis is resolved, remaining candidates are dominated, diminishing returns fall below materiality, or continuing requires changing the plan;
- **diagnosis before intervention:** distinguish overfit, leakage, instability, objective mismatch, subgroup failure, calibration failure, drift, and data-quality problems before expanding search;
- **refresh versus new research:** prefer recalibration/retraining when lifecycle evidence supports the existing hypothesis; open new research only for a structural unresolved question;
- **meta-model safety:** require OOF/cross-fitted upstream predictions for downstream fitting, matched controls/ablations, incremental-value evidence, and explicit rejection of unsupported nested graph depth;
- **inconclusive evidence:** do not force a winner when variation or missing evidence prevents a reliable decision;
- **capability escalation:** create a bounded capability request instead of implementing missing software ad hoc inside the research loop.

## Reliability checks

Automo validates that each task class resolves to existing packaged Markdown, includes its required safety documents, and stays within the selection-size bound. Tests also exercise documented CLI entry points and a synthetic multi-milestone walkthrough.

See `examples/research-guidance/` for a sequence containing a rejected feature hypothesis, an accepted model-family intervention, and a rejected recalibration intervention without OOS leakage or unbounded search.
