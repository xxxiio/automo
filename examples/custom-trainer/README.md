# Custom trainer example

A synthetic `ModelTrainer` delegates fitting to an injected service and returns a custom predictor. No domain-specific package is required.

```bash
python examples/custom-trainer/example.py
```

Expected output contains an `agreement` score.

Next: `docs/trainers-and-graphs.md`.
