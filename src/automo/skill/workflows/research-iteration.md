# Research iteration workflow

## Trigger
Use for every governed Automo research iteration.

## Procedure
1. Read `.automo/project.yaml`, `.automo/current/milestone.yaml`, and `.automo/current/next-step.yaml`.
2. If project mode is `plan`, do not fit models or inspect sealed OOS; perform only planning work.
3. When research mode is active, execute exactly one committed bounded step.
4. Record every candidate, exposure, metric, failure, and capability blocker through Automo artifacts.
5. After evidence is available, decide accepted, rejected, inconclusive, or invalid without rewriting prior evidence.
6. Emit exactly one next research step or conclude the milestone.

## Stop conditions
Stop when the milestone question is answered, the committed budget is exhausted, required data/capability is unavailable, or further work cannot change the conclusion.

## Operational entry points
Use `automo status` and `automo plan` to inspect governed state. Use `automo guidance --task-class <task-class>` to load the minimum task-specific guidance. Milestone lifecycle actions live under `automo research milestone-create`, `automo research milestone-transition`, `automo research milestone-status`, and `automo research milestone-conclude`.
