# Research project governance

Automo owns mutable model-research state under `.automo/`. GetDone, when used for software development, owns `.agent/`. The two directories have different authority and must not be merged.

A fresh `automo init` creates:

```text
.automo/
├── project.yaml
├── roadmap.yaml
├── current/
│   └── next-step.yaml
└── milestones/
```

Registry, research-run, pool, refresh, and capability state also live below `.automo/` as they are created.

## Research milestone lifecycle

A milestone is a bounded scientific question rather than a software feature. Its lifecycle is:

```text
proposed → planning → approved → active → concluded
```

Only an `active` milestone permits governed automated research execution. Proposed, planning, and approved milestones remain in plan mode. Concluded milestones record exactly one outcome: `accepted`, `rejected`, `inconclusive`, or `invalid`.

Example:

```bash
automo research milestone-create R001 \
  --question "Does the candidate improve the committed objective?" \
  --why-next "This is the highest-value unresolved question." \
  --exit-criterion "candidate evaluated" \
  --exit-criterion "conclusion recorded"

automo research milestone-transition R001 --status planning
automo research milestone-transition R001 --status approved
automo research milestone-transition R001 --status active
```

After evidence is complete:

```bash
automo research milestone-conclude R001 \
  --outcome rejected \
  --conclusion "No material improvement under the committed protocol."
```

A negative conclusion is valid completed research. The project returns to plan mode and must select the next highest-priority question before further research execution.

## GetDone boundary

When research requires missing software capability, Automo persists a bounded capability request under `.automo/capabilities/requests/`. Optional GetDone delegation may implement that capability, using `.agent/` for its own development workflow state. Automo protects `.automo/` research evidence from delegated mutation and independently validates the returned implementation result before research resumes.
