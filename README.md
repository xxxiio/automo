# Automo

Automo is a deterministic framework for model research, evaluation, lifecycle management, and bounded automated optimisation. It is designed for ordinary supervised models, custom training pipelines, structured outputs, and composable model graphs without requiring domain-specific logic in the core package.

Automo owns the reusable research machinery: data snapshots and partitions, fit/validation/OOS governance, model lineage, calibration lineage, model pools, refresh evaluation, bounded research, cross-fitted model graphs, and immutable evidence. Project packages provide the thin domain layer: data sources, features, model trainers, evaluators, and optional external services.

GetDone integration is optional. Automo runs standalone.

## Install

```bash
python -m pip install automo
```

For first-time local development, install Poetry and use the PPW-style repository bootstrap:

```bash
python scripts/init_dev.py
poetry run pre-commit run --all-files
poetry run pytest -q
```

The bootstrap runs `poetry install --with dev` and installs/pre-provisions the Git pre-commit hook for the clone. Ordinary `git commit` then runs the configured hooks automatically.

## Start a project

```bash
automo init --root my-project
cd my-project
automo validate
automo doctor
```

`automo init` creates a minimal `automo.toml` and `automo_project.py`. Add your data sources, features, models, trainers, evaluators, and services to that project plugin.

## Core workflows

```bash
automo status
automo plan
automo run
automo validate

automo models --help
automo refresh --help
automo research --help
```

Refresh uses explicit fit/validation/refresh-OOS partitions when fitted state changes. Data does not need a datetime column: predefined, stable-hash, grouped, ordered-ID, and temporal split strategies are supported.

Custom `ModelTrainer` hooks can fully control fitting, including delegation to external packages or services. Model graphs can consume outputs from upstream models; downstream/meta-model fitting uses cross-fitted upstream predictions to avoid stacking leakage.

## Learn by example

Small synthetic examples are under `examples/`:

- `basic-supervised` — built-in tabular regression path.
- `custom-trainer` — delegate fitting to an injected service.
- `meta-model` — leakage-safe stacking with cross-fitted upstream outputs.
- `structured-output` — arbitrary structured model outputs.
- `id-only-data` — deterministic splitting without timestamps.
- `end-to-end` — a compact project/runtime/registry walkthrough.

Start with [Getting started](docs/getting-started.md), then see [Agent research guidance](docs/agent-guidance.md), [Public API](docs/public-api.md), [Trainers and graphs](docs/trainers-and-graphs.md), [Model registry](docs/model-registry.md), [Refresh](docs/refresh.md), and [Bounded research](docs/research.md).

## Alpha status

`0.3.0a1` is the first intentionally public alpha. Persistent public artifacts carry an artifact type and schema version, but APIs may still evolve during the alpha series. See the [public alpha release contract](docs/release-contract.md) for supported boundaries and known limitations.

## Security

Automo does not sandbox project plugins, trainers, evaluators, codecs, calibrators, injected services, or delegated workflow providers. Only run trusted extension code and load trusted model artifacts. See [SECURITY.md](SECURITY.md).

## Development workflow

This repository uses pre-commit as the canonical source-quality gate. Repository/configuration hygiene and Ruff formatting/linting are configured as hooks, and CI runs that same configuration directly. GetDone project records under `.agent/` are development metadata for this repository and are not required at runtime.


## Project-specific research guidance

Keep mutable research state under `.automo/` and project-owned agent instructions under `.project-agent/automo/`. `automo guidance` discovers `.project-agent/automo/index.json` additively by default; use `--no-project-agent` for canonical Automo-only guidance. Pin a reviewed composition with `automo guidance-lock --write` and verify it with `automo guidance-check`. Project guidance may strengthen or specialize research rules but cannot replace protected sealed-OOS, bounded-search, evidence, or milestone-governance rules.
