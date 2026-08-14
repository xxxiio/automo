---
template: milestone-plan
template_version: 2.0.0
project_owned: true
record_contract: milestone-plan
record_schema_version: 1
id: MILESTONE-0013
status: active
---

# MILESTONE-0013 — Public alpha hardening

## Intended outcome

Automo `0.3.0a1` is publishable as the first intentional public alpha with a clean package identity, versioned persistence, documented extension/security contracts, reproducible onboarding, and verified wheel/sdist installation.

## Why this milestone matters

The research/runtime architecture is complete enough for external use. Remaining risk is release hygiene and supportability rather than missing research features.

## Scope

- Automo-only package/CLI identity and clean source tree.
- One package-version source.
- Explicit public persistence schema envelopes.
- Documented public Python API and trusted-code boundary.
- Fresh-project `init`/`validate`/`doctor` path.
- Synthetic focused and end-to-end onboarding examples.
- Controlled CLI errors for common user mistakes.
- Wheel and sdist build/install smoke gates.
- Python 3.11–3.13 test matrix plus one canonical pre-commit quality gate combining repository hygiene with Ruff lint/format.
- Public README, changelog, roadmap, release contract, and security documentation.

## Non-goals

- New research algorithms, deployment, distributed training, deeper graph cross-fitting, or domain-specific examples.

## Deliverables

- `automo 0.3.0a1` release candidate artifacts.
- Versioned persistence helper and updated stores.
- Clean packaging/CI/pre-commit configuration.
- Public onboarding/security/API/release documentation.

## Dependencies

- MILESTONE-0012 completed.

## Risks

- The current offline environment cannot provision the remote pre-commit hook environments; the configured CI gate must provide final EC-013 execution evidence.

## Ordered implementation sequence

1. Remove legacy/generated package state.
2. Add persistence schema envelopes and one version source.
3. Harden public API, initialization, plugin loading, and CLI errors.
4. Complete public docs and onboarding examples.
5. Verify wheel/sdist release artifacts offline.
6. Run the complete pre-commit hook set once through CI and run tests across Python 3.11–3.13.

## Exit criteria

- [x] EC-001: No legacy package/CLI identity ships.
- [x] EC-002: Clean source/release artifacts exclude generated runtime/build state.
- [x] EC-003: Version metadata has one source of truth.
- [x] EC-004: Public persisted artifact families have explicit artifact type/schema version metadata.
- [x] EC-005: Supported public Python extension imports are documented and tested.
- [x] EC-006: Extension/model-artifact trust boundaries are documented.
- [x] EC-007: A freshly initialized project validates and passes doctor without internal fixtures.
- [x] EC-008: Six synthetic onboarding examples run, including one compact end-to-end example.
- [x] EC-009: Common missing-ID CLI errors are controlled and traceback-free.
- [x] EC-010: Clean wheel installation and smoke workflow pass.
- [x] EC-011: Clean sdist installation and smoke workflow pass.
- [ ] EC-012: Python 3.11, 3.12, and 3.13 CI passes for the release candidate.
- [ ] EC-013: CI executes the complete repository pre-commit hook set, including repository/configuration hygiene and Ruff lint/format, successfully.
- [x] EC-014: Public release documentation and terminology are release-ready.

## Evidence

- EC-001/002: `pyproject.toml`, `MANIFEST.in`, `scripts/source_check.py`, release health gate.
- EC-003: `src/automo/_version.py` plus dynamic setuptools metadata.
- EC-004: `src/automo/persistence/`, registry/research/refresh stores, legacy evidence artifact types, tests.
- EC-005: `src/automo/__init__.py`, `docs/public-api.md`, `tests/test_public_release.py`.
- EC-006: `SECURITY.md` and release contract.
- EC-007/008/009: public release tests and examples.
- EC-010/011: `python scripts/health_gate.py --keep-dist`.
- EC-012/013: `.github/workflows/ci.yml` and `.pre-commit-config.yaml`; execution evidence not available in this offline environment.
- EC-014: README, CHANGELOG, ROADMAP, docs index/getting-started/user guide/release contract.

## Remaining work

- EC-012 and EC-013 require one connected CI run across the configured Python matrix.

## Next milestone

none
