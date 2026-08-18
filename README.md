# Automo

Automo is a deterministic framework for model research, evaluation, lifecycle management, and bounded automated optimisation. It is designed for ordinary supervised models, custom training pipelines, structured outputs, and composable model graphs without requiring domain-specific logic in the core package.

Automo owns the reusable research machinery: data snapshots and partitions, fit/validation/OOS governance, model lineage, calibration lineage, model pools, refresh evaluation, bounded research, cross-fitted model graphs, and immutable evidence. Project packages provide the thin domain layer: data sources, features, model trainers, evaluators, and optional external services.

GetDone integration is optional. Automo runs standalone.

## Install

```bash
python -m pip install automo
```

For first-time local development, use the uv repository bootstrap:

```bash
python scripts/init_dev.py
uv run pre-commit run --all-files --show-diff-on-failure
```

The bootstrap installs `uv` with the currently selected Python when it is missing, syncs the project environment from `pyproject.toml`, and installs the standard clone-local pre-commit hook. `uv` owns Python/environment/dependency execution for development. Ordinary `git commit` runs the repository hooks plus the always-run pytest unit-test hook. The explicit local full-repository gate is `uv run pre-commit run --all-files --show-diff-on-failure`, which matches the GitHub quality job; GitHub separately runs pytest on Python 3.11, 3.12, and 3.13.

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

Start with [Getting started](https://xxxiio.github.io/automo/getting-started/), then see [Agent research guidance](https://xxxiio.github.io/automo/agent-guidance/), [Public API](https://xxxiio.github.io/automo/public-api/), [Trainers and graphs](https://xxxiio.github.io/automo/trainers-and-graphs/), [Model registry](https://xxxiio.github.io/automo/model-registry/), [Refresh](https://xxxiio.github.io/automo/refresh/), and [Bounded research](https://xxxiio.github.io/automo/research/).

## Alpha status

`0.3.0a2` is the current public alpha and adds hierarchical multi-model research composition on top of the initial alpha runtime. Persistent public artifacts carry an artifact type and schema version, but APIs may still evolve during the alpha series. See the [public alpha release contract](https://xxxiio.github.io/automo/release-contract/) for supported boundaries and known limitations.

## Security

Automo does not sandbox project plugins, trainers, evaluators, codecs, calibrators, injected services, or delegated workflow providers. Only run trusted extension code and load trusted model artifacts. See [security policy](https://github.com/xxxiio/automo/blob/main/SECURITY.md).

## Development workflow

This repository uses uv plus pre-commit as the development gate. Repository/configuration hygiene, Ruff formatting/linting, and `uv run pytest -q` run through the uv-managed project environment. GitHub uses uv for the same gate and separately runs pytest on Python 3.11, 3.12, and 3.13. GetDone project records under `.agent/` are development metadata for this repository and are not required at runtime.


## Research program structure

Automo keeps scientific research state separate from project-management direction. GetDone or another project system owns roadmap/milestone guidance; Automo owns the model graph, falsifiable hypothesis hierarchy, experiments, evidence, and scientific conclusions.

The model graph supports independent models, submodel → meta-model composition (`input` relations), and flat informational relationships such as `correlated` or `complementary`. The hypothesis hierarchy is a separate graph: scientific parent/child claims do not have to mirror runtime model dependencies. Governed automated research binds plans and capability requests to program → hypothesis → experiment provenance.

```bash
automo research model-add ranking --role submodel
automo research model-add meta --role meta
automo research model-relation-add ranking meta --kind input
automo research hypothesis-create H-RANK \
  --statement "Ranking adds incremental information." \
  --primary-model ranking \
  --related-model meta \
  --objective ndcg:local:maximize \
  --objective meta_log_loss:parent:minimize \
  --evaluation-depth parent
automo research hypothesis-activate H-RANK

# Register immutable model candidates and their exact composition.
automo research candidate-add RANK-v1 --model ranking --model-spec-id ranking-v1 --artifact-id MODEL-RANK-v1
automo research candidate-add META-v1 --model meta --model-spec-id meta-linear --artifact-id MODEL-META-v1 \
  --input ranking:RANK-v1
```

Composition/ablation experiments are first-class research artifacts. Each immutable composed-model candidate pins its exact upstream candidate versions; experiments compare two such candidates, so Automo can distinguish standalone model improvements from incremental meta-model value. See [Research governance](https://xxxiio.github.io/automo/research-governance/).

## Project-specific research guidance

Keep mutable research state under `.automo/` and project-owned agent instructions under `.project-agent/automo/`. `automo guidance` discovers `.project-agent/automo/index.json` additively by default; use `--no-project-agent` for canonical Automo-only guidance. Pin a reviewed composition with `automo guidance-lock --write` and verify it with `automo guidance-check`. Project guidance may strengthen or specialize research rules but cannot replace protected sealed-OOS, bounded-search, evidence, or hypothesis-governance rules.
