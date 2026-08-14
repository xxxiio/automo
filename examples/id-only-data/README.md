# ID-only data example

Automo does not require datetime columns. This example uses a stable hash of an ID to produce deterministic fit/validation/test partitions.

```bash
python examples/id-only-data/example.py
```

Expected output is three partition sizes whose total is 20.

Next: `docs/refresh.md` for ordered, grouped, predefined, and temporal split semantics.
