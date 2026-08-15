# Automo 0.3.0a1 public alpha contract

`0.3.0a1` is the first intentionally public Automo alpha.

## Supported use cases

- deterministic fit/validation/OOS research;
- user-defined data sources, features, trainers, evaluators, and external services;
- model registry, calibration lineage, lifecycle history, and benchmark evidence;
- model pools and data-iteration refresh workflows;
- bounded automated research with explicit budgets and OOS gates;
- composable model graphs and leakage-safe first-level stacking/meta-model training;
- datasets using time, ordered IDs, groups, stable hashes, or predefined partitions.

## Not claimed

The alpha does not promise globally optimal model search, production deployment, distributed training, arbitrary online learning, deep recursively nested cross-fitting, or sandboxing of third-party code.

## Persistent artifacts

Public registry, refresh, pool, and research artifacts are written with `artifact_type` and `schema_version`. The initial public schema version is `1`.

## Extension-code trust

Project plugins, trainers, evaluators, codecs, calibrators, injected services, and workflow providers run with normal Python process privileges. See `SECURITY.md`.

## Release gate

The release candidate must pass the canonical full-repository pre-commit gate locally and in CI. That gate includes repository hygiene, Ruff lint/format, and pytest locally plus GitHub Python 3.11, 3.12, and 3.13 compatibility jobs. Source compilation, runnable examples, and wheel/sdist build/install smoke tests remain separate release gates.

## Agent research governance

The public alpha includes packaged agent-facing research guidance, `.automo/` milestone/plan-mode governance, and an optional bounded GetDone capability handoff. GetDone development state remains separate under `.agent/`.
