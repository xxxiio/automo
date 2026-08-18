# Research-guidance walkthrough

This synthetic example demonstrates how an agent should use Automo guidance across several falsifiable research hypotheses without turning research into an open-ended tuning loop.

Run from a source checkout:

```bash
python examples/research-guidance/example.py
```

The walkthrough deliberately includes a rejected feature hypothesis, a supported bounded model-family hypothesis, and a rejected recalibration hypothesis. Each hypothesis records one scientific claim, a fixed candidate/OOS budget, a materiality threshold, explicit evidence, and an explicit project implication.

The key sequence is:

```text
project direction -> active hypothesis -> bounded experiment -> evidence -> diagnosis -> hypothesis conclusion
```

The example also lists actions an agent must refuse: sealed-OOS candidate generation, hiding failed candidates, unplanned search expansion, and confounded multi-dimensional interventions.

Next: run `automo guidance --task-class hypothesis-planning`, then read `docs/agent-guidance.md`.
