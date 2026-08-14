# Meta-model example

A small synthetic stacking graph. The downstream model consumes upstream model outputs and Automo creates out-of-fold upstream predictions for meta-model fitting.

```bash
python examples/meta-model/example.py
```

Expected output prints cross-fit metadata. The trainer asserts that memorized in-sample upstream predictions never reach the meta-model fit.

Next: `docs/trainers-and-graphs.md`.
