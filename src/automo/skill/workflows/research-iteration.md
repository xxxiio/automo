# Research iteration workflow

## Trigger
Use for every governed Automo research iteration.

## Procedure
1. Read `.automo/project.yaml`, `.automo/research-program/program.yaml`, the model graph, and the active hypothesis.
2. Treat GetDone/project roadmap material as external prioritization context only; do not reproduce milestone state in Automo.
3. Execute research only when a falsifiable hypothesis is active.
4. Bind every research plan, experiment, capability request, evidence artifact, and conclusion to program/hypothesis/experiment provenance.
5. Evaluate the intervention at the hypothesis's committed depth: validity, local, parent, or system.
6. Preserve every candidate, exposure, metric, failure, and capability blocker through Automo artifacts.
7. Conclude the hypothesis as supported, rejected, or inconclusive when evidence is sufficient; otherwise choose the next bounded experiment for the same hypothesis.

## Model-structure rules
- Independent models may coexist without dependency relations.
- Use `input` relations for actual submodel/meta-model composition.
- Use `correlated` or `complementary` relations for informational relationships that are not execution dependencies.
- Keep the model graph separate from the hypothesis hierarchy.

## Stop conditions
Stop when the active hypothesis is sufficiently resolved at its required evaluation depth, the committed budget is exhausted, required data/capability is unavailable, or further work cannot change the conclusion.

## Operational entry points
Use `automo status` and `automo plan` to inspect governed state. Use `automo guidance --task-class <task-class>` to load the minimum task-specific guidance. Manage model structure with `automo research model-add` and `automo research model-relation-add`; manage scientific claims with `automo research hypothesis-create`, `automo research hypothesis-activate`, `automo research hypothesis-tree`, and `automo research hypothesis-conclude`.
