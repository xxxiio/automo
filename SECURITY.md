# Security Policy

Automo is an early-alpha model-research framework. Treat extension code, model artifacts, datasets, and external services as trusted-code boundaries rather than sandboxed content.

## Reporting a vulnerability

Report suspected vulnerabilities privately to the project maintainers rather than publishing exploit details in a public issue.

## Code-execution boundary

Automo does **not** sandbox Python extensions. The following may execute arbitrary code with the privileges of the current Python process:

- `ResearchPlugin` factories;
- `ModelTrainer` and legacy `ModelRunner` implementations;
- `Evaluator` and feature-computation implementations;
- model and calibration artifact codecs;
- calibrators;
- injected project services;
- optional delegated workflow providers, including GetDone integrations.

Only install or load extensions you trust. Run untrusted projects in an isolated environment or container.

## Model artifacts and codecs

A codec controls how an artifact is deserialized. Some ecosystem formats, including pickle-compatible formats, can execute code while loading. Automo cannot make an unsafe third-party serialization format safe. Only load model or calibration artifacts from trusted sources and verify provenance/hash information before use.

## Data and external services

Custom trainers/evaluators can pass project data to injected services. Project authors are responsible for deciding which services may receive data and for protecting credentials. Do not put secrets, access tokens, or private keys in model manifests, research evidence, refresh reports, or other persisted Automo artifacts.

## Integrity controls

Automo uses immutable evidence, hashes, versioned persistent artifacts, bounded capability scopes, and explicit lifecycle transitions to improve auditability. These controls detect or constrain many accidental mutations, but they are not an operating-system security boundary.
