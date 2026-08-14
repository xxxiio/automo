"""Deterministic findings and next-experiment proposal from immutable evidence."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


class FindingError(RuntimeError):
    """Raised when findings cannot be derived safely."""


@dataclass(frozen=True)
class FindingResult:
    run_id: str
    findings_path: Path
    next_experiment_path: Path
    next_experiment_id: str


def propose_next_experiment(root: Path, run_id: str) -> FindingResult:
    run_dir = root / "runs" / run_id
    decision_path = run_dir / "decision.json"
    dispositions_path = run_dir / "feature-dispositions.json"
    findings_path = run_dir / "findings.json"
    if findings_path.exists():
        raise FindingError(f"findings already exist for immutable run: {run_id}")
    decision = _read_mapping(decision_path)
    dispositions = _read_mapping(dispositions_path)
    outcome = decision.get("outcome")
    rows = dispositions.get("dispositions")
    if not isinstance(rows, list) or not rows:
        raise FindingError("feature dispositions must contain at least one result")

    retained = [r["feature_group_id"] for r in rows if r.get("outcome") == "retained"]
    rejected = [r["feature_group_id"] for r in rows if r.get("outcome") == "rejected"]
    inconclusive = [r["feature_group_id"] for r in rows if r.get("outcome") == "inconclusive"]

    if outcome == "accepted" and retained:
        diagnosis = "promising-but-under-evidenced"
        rationale = (
            "The candidate passed the committed decision gates and at least one feature group was retained, "
            "but the current fixture is too small to justify bounded model search or promotion."
        )
        next_id = "EXPERIMENT-0002"
        title = "Confirm candidate stability across predefined temporal folds"
        hypothesis = (
            "The accepted linear candidate with the retained core feature group will preserve directional "
            "improvement across predefined temporal folds without changing the frozen feature set."
        )
        falsification = [
            "Any predefined fold shows candidate degradation beyond the committed stability tolerance.",
            "Aggregate validation and out-of-sample direction no longer agree.",
        ]
    elif outcome in {"rejected", "inconclusive"}:
        diagnosis = "candidate-not-confirmed"
        rationale = "The completed evidence does not justify expanding search; the next experiment must increase evidence quality while keeping scope bounded."
        next_id = "EXPERIMENT-0002"
        title = "Repeat the candidate under a predefined temporal stability protocol"
        hypothesis = "A predefined temporal stability protocol will determine whether the current candidate effect is reproducible."
        falsification = ["The candidate fails directional agreement across predefined folds."]
    else:
        raise FindingError(f"unsupported decision outcome for next-experiment generation: {outcome!r}")

    experiment_path = root / "research" / "experiments" / f"{next_id}.yaml"
    if experiment_path.exists():
        raise FindingError(f"next experiment already exists: {experiment_path}")

    source_experiment = root / "research" / "experiments" / f"{decision['experiment_id']}.yaml"
    source = yaml.safe_load(source_experiment.read_text(encoding="utf-8"))
    candidate = source["candidate"]
    next_spec = {
        "id": next_id,
        "objective": source["objective"],
        "status": "ready",
        "title": title,
        "why_next": rationale,
        "hypothesis": hypothesis,
        "rationale": [
            f"Completed decision outcome: {outcome}.",
            f"Retained feature groups: {', '.join(retained) if retained else 'none'}.",
            "Stability evidence is required before bounded model or feature search.",
        ],
        "expected_effect": "Produce stable directional evidence across predefined temporal folds.",
        "falsification": falsification,
        "baseline": source["baseline"],
        "candidate": candidate,
        "data": source["data"],
        "capabilities": source.get("capabilities", []) + [
            {"id": "CAPABILITY-TEMPORAL-STABILITY-0001", "kind": "evaluation-protocol"}
        ],
        "split_spec": "SPLIT-PREDEFINED-TEMPORAL-FOLDS-0001",
        "evaluation_spec": "EVALUATION-TEMPORAL-STABILITY-0001",
        "decision_policy": source["decision_policy"],
        "budget": {"maximum_trials": 3, "maximum_runtime_minutes": 15, "maximum_compute_cost": 0},
    }

    evidence = {
        "decision": {"path": "decision.json", "sha256": _sha256(decision_path)},
        "feature_dispositions": {"path": "feature-dispositions.json", "sha256": _sha256(dispositions_path)},
    }
    findings = {
        "artifact_type": "automo.findings",
        "schema_version": 1,
        "run_id": run_id,
        "experiment_id": decision["experiment_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "diagnosis": diagnosis,
        "findings": [
            {"id": "FINDING-0001", "kind": "experiment-decision", "statement": f"Experiment outcome was {outcome}."},
            {"id": "FINDING-0002", "kind": "feature-usefulness", "statement": f"Retained={retained}; rejected={rejected}; inconclusive={inconclusive}."},
            {"id": "FINDING-0003", "kind": "evidence-limit", "statement": "The local fixture is insufficient for promotion or broad search."},
        ],
        "evidence": evidence,
        "next_experiment": {
            "id": next_id,
            "path": str(experiment_path.relative_to(root)),
            "why_next": rationale,
            "falsification": falsification,
            "count": 1,
        },
        "completed_evidence_modified": False,
    }

    experiment_path.write_text(yaml.safe_dump(next_spec, sort_keys=False), encoding="utf-8")
    findings_path.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return FindingResult(run_id, findings_path, experiment_path, next_id)


def _read_mapping(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FindingError(f"invalid JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise FindingError(f"evidence must be a mapping: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
