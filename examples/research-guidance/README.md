# Research-guidance walkthrough

This synthetic example demonstrates how an agent should use Automo guidance across several research milestones without turning research into an open-ended tuning loop.

Run from a source checkout:

```bash
python examples/research-guidance/example.py
```

The walkthrough deliberately includes a rejected feature hypothesis, an accepted bounded model-family intervention, and a rejected recalibration intervention. Each milestone records one question, a fixed candidate/OOS budget, a materiality threshold, explicit evidence, and exactly one next step.

The key sequence is:

```text
plan mode -> active milestone -> bounded experiment -> evidence -> diagnosis -> conclusion -> plan mode
```

The example also lists actions an agent must refuse: sealed-OOS candidate generation, hiding failed candidates, unplanned search expansion, and confounded multi-dimensional interventions.

Next: run `automo guidance --task-class milestone-planning`, then read `docs/agent-guidance.md`.
