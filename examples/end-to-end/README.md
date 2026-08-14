# End-to-end example

This compact synthetic example connects a project plugin, built-in trainer, filesystem model registry,
artifact reload, and benchmark recording.

Run from a source checkout:

```bash
python examples/end-to-end/example.py
```

Expected output includes a generated `MODEL-...` identifier, lifecycle status `candidate`, and a near-zero
MSE. The example uses a temporary directory and leaves no runtime state in the repository.

Next: read `docs/model-registry.md`, then `docs/research.md` and `docs/refresh.md` for the governed
research and ongoing model-lifecycle workflows.
