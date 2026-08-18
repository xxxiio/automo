# Project-Agent Research Extensions

## Trigger
Use when a consuming project defines research-specific agent guidance under `.project-agent/automo/`.

## Required boundary
- Automo `skill/` is canonical read-only research guidance.
- `.project-agent/automo/` is project-owned, additive Automo research guidance; the root `.project-agent/index.json` is reserved for other consumers such as GetDone.
- `.automo/` is mutable research state and must not contain canonical project instruction prose.
- Project-agent guidance may specialize or strengthen Automo rules but must not disable sealed-OOS, bounded-search, evidence, or hypothesis-governance invariants.

## Index contract
`.project-agent/automo/index.json` uses schema version 1 and may define `rules` with string `concerns` and safe relative Markdown paths in `load`. Automo discovers rules for the current task class plus explicit `--concern` values.

## Reproducibility
Pin accepted compositions with `automo guidance-lock --write`. Research evidence should retain the resulting composition digest when guidance changes are material to interpretation.

## Completion
The project-agent index validates, all referenced files exist, selection stays bounded, and `automo guidance-check` reports a current or intentionally absent lock.
