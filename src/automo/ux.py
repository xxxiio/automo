"""High-level project UX for Automo.

The low-level research commands remain deterministic primitives. This module provides
GetDone-like project navigation without hiding or skipping governance boundaries.
"""

from __future__ import annotations

import importlib.metadata
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from automo.contracts import ExperimentSpec
from automo.execution import run_temporal_stability
from automo.execution.local import ExecutionError
from automo.governance import ResearchGovernance
from automo.guidance import guidance_lock, validate_project_agent
from automo.integrations.getdone import GetDoneCapabilityWorkflow
from automo.project import ResearchProject
from automo.runtime.plugin import PluginLoadError, load_project_plugin


@dataclass(frozen=True)
class ProjectStatus:
    root: Path
    objective_id: str
    objective_status: str
    experiment_id: str
    experiment_title: str
    experiment_status: str
    stage: str
    next_action: str
    evidence: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "objective": {"id": self.objective_id, "status": self.objective_status},
            "experiment": {
                "id": self.experiment_id,
                "title": self.experiment_title,
                "status": self.experiment_status,
            },
            "stage": self.stage,
            "next_action": self.next_action,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str
    blocking: bool = False


def package_version() -> str:
    try:
        installed = importlib.metadata.version("automo")
        if installed:
            return installed
    except (importlib.metadata.PackageNotFoundError, KeyError):
        pass

    from automo import __version__

    return __version__


def initialise_mr_project(root: Path) -> tuple[Path, ...]:
    """Create a minimal standalone Automo project without overwriting project state."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    directories = (
        Path("research/objectives"),
        Path("research/experiments"),
        Path("research/features"),
        Path("research/policies"),
        Path("data"),
    )
    for relative in directories:
        path = root / relative
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(relative)

    files = {
        Path("automo.toml"): '[project]\nplugin = "automo_project:create_plugin"\n',
        Path("automo_project.py"): (
            '"""Minimal Automo project plugin. Add data sources, features, models, and metrics here."""\n\n'
            "from automo import ResearchPlugin\n\n\n"
            "def create_plugin() -> ResearchPlugin:\n"
            "    return ResearchPlugin(\n"
            '        id="my-project",\n'
            "        data_sources=(),\n"
            "        feature_computers=(),\n"
            "        feature_sets=(),\n"
            "        objectives=(),\n"
            "        metrics=(),\n"
            "        model_specs=(),\n"
            "        model_runners=(),\n"
            "    )\n"
        ),
        Path("README.md"): (
            "# Automo project\n\n"
            "Start by editing `automo_project.py`, then run `automo validate` and `automo doctor`.\n"
        ),
    }
    for relative, content in files.items():
        path = root / relative
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(relative)
    created.extend(ResearchGovernance(root).initialise())
    project_agent = root / ".project-agent" / "automo"
    if not project_agent.exists():
        project_agent.mkdir(parents=True)
        created.append(project_agent.relative_to(root))
    agent_baseline = project_agent / "AGENTS.md"
    if not agent_baseline.exists():
        agent_baseline.write_text(
            "# Project-specific Automo research guidance\n\n"
            "Add durable project research rules here. Keep mutable research state in `.automo/`.\n",
            encoding="utf-8",
        )
        created.append(agent_baseline.relative_to(root))
    agent_index = project_agent / "index.json"
    if not agent_index.exists():
        agent_index.write_text(
            '{\n  "schema_version": 1,\n  "infer": [],\n  "rules": []\n}\n', encoding="utf-8"
        )
        created.append(agent_index.relative_to(root))
    return tuple(created)


def project_status(root: Path) -> ProjectStatus:
    root = root.resolve()
    project = ResearchProject(root)
    objective = project.objective()
    experiment = project.next_experiment()
    evidence, stage, action = _experiment_state(root, experiment)
    return ProjectStatus(
        root=root,
        objective_id=objective.identifier,
        objective_status=objective.status,
        experiment_id=experiment.identifier,
        experiment_title=experiment.title,
        experiment_status=experiment.status,
        stage=stage,
        next_action=action,
        evidence=tuple(evidence),
    )


def render_status(status: ProjectStatus) -> str:
    lines = [
        "# Automo Status",
        "",
        "Objective",
        f"- {status.objective_id}",
        f"- status: {status.objective_status}",
        "",
        "Current experiment",
        f"- {status.experiment_id}",
        f"- {status.experiment_title}",
        "",
        "Evidence",
    ]
    lines.extend(f"- {name}: {state}" for name, state in status.evidence)
    lines.extend(["", "Next deterministic step", f"- {status.next_action}", ""])
    return "\n".join(lines)


def doctor_checks(root: Path) -> tuple[DoctorCheck, ...]:
    root = root.resolve()
    checks: list[DoctorCheck] = [DoctorCheck("Automo installation", "pass", package_version())]
    has_config = (root / "automo.toml").is_file()
    has_research_state = (root / ".automo" / "project.yaml").is_file()
    checks.append(
        DoctorCheck(
            "Automo project",
            "pass" if has_config and has_research_state else "fail",
            str(root),
            blocking=not (has_config and has_research_state),
        )
    )
    if has_config:
        try:
            plugin = load_project_plugin(root)
        except PluginLoadError as exc:
            checks.append(DoctorCheck("Project plugin", "fail", str(exc), blocking=True))
        else:
            checks.append(DoctorCheck("Project plugin", "pass", plugin.id))
    governance_errors = ResearchGovernance(root).validate()
    checks.append(
        DoctorCheck(
            "Research governance",
            "fail" if governance_errors else "pass",
            "; ".join(governance_errors)
            if governance_errors
            else "program/model/hypothesis state valid",
            blocking=bool(governance_errors),
        )
    )
    integration = GetDoneCapabilityWorkflow(enabled=False).status()
    checks.append(
        DoctorCheck(
            "GetDone integration",
            "pass" if integration.installed else "optional",
            integration.detail,
        )
    )
    checks.append(
        DoctorCheck(
            "GetDone project records",
            "pass" if (root / ".agent").is_dir() else "optional",
            ".agent/ present" if (root / ".agent").is_dir() else "not bootstrapped",
        )
    )
    for command, required in (("python", True), ("git", False)):
        executable = shutil.which(command)
        checks.append(
            DoctorCheck(
                f"{command} executable",
                "pass" if executable else ("fail" if required else "optional"),
                executable or "not installed",
                blocking=required and executable is None,
            )
        )
    return tuple(checks)


def validate_project(root: Path) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    """Validate MR contracts and, when available, GetDone 1.1+ project records."""
    errors: list[str] = []
    warnings: list[str] = []
    root = root.resolve()
    has_config = (root / "automo.toml").is_file()
    if has_config:
        try:
            load_project_plugin(root)
        except PluginLoadError as exc:
            errors.append(str(exc))
    else:
        errors.append(f"Automo project config is missing: {root / 'automo.toml'}")

    governance_errors = ResearchGovernance(root).validate()
    errors.extend(governance_errors)
    errors.extend(validate_project_agent(root))
    if (root / ".project-agent" / "automo").is_dir():
        lock_status, _ = guidance_lock(root)
        if lock_status == "missing":
            warnings.append(
                "Automo guidance composition is not pinned; run automo guidance-lock --write after review"
            )
        elif lock_status != "current":
            errors.append(
                f"Automo guidance composition is {lock_status}; review and rewrite the guidance lock"
            )

    if (root / ".agent").is_dir():
        try:
            from getdone.initialise_project import repository_root
            from getdone.validate_project import validate_project as validate_getdone
        except (ImportError, ModuleNotFoundError):
            warnings.append("GetDone is not installed; .agent contract validation was skipped")
        else:
            report = validate_getdone(root, skills_root=repository_root(), profile="standard")
            errors.extend(f"{item.path}: {item.message}" for item in report.errors)
            warnings.extend(f"{item.path}: {item.message}" for item in report.warnings)
    return not errors, tuple(errors), tuple(warnings)


def run_next_transition(root: Path, *, run_id: str | None = None) -> tuple[str, Path]:
    """Execute exactly one legal transition for the committed current experiment."""
    root = root.resolve()
    experiment = ResearchProject(root).next_experiment()
    evidence, stage, _ = _experiment_state(root, experiment)
    del evidence
    if stage == "temporal-stability-pending":
        result = run_temporal_stability(root, experiment, run_id=run_id)
        return "temporal-stability", result.evidence_path
    if stage == "temporal-stability-complete":
        raise ExecutionError(
            "the current experiment's committed temporal-stability transition is already complete; "
            "a new experiment or promotion decision must be committed before another run"
        )
    raise ExecutionError(
        f"no high-level transition is registered for evaluation spec {experiment.evaluation_spec!r}; "
        "use the advanced experiment commands"
    )


def plan_payload(root: Path) -> dict[str, Any]:
    experiment = ResearchProject(root.resolve()).next_experiment()
    return {
        "id": experiment.identifier,
        "status": experiment.status,
        "title": experiment.title,
        "why_next": experiment.why_next,
        "hypothesis": experiment.hypothesis,
        "rationale": list(experiment.rationale),
        "expected_effect": experiment.expected_effect,
        "falsification": list(experiment.falsification),
        "baseline": experiment.baseline,
        "candidate_model": experiment.candidate_model,
        "feature_set": experiment.feature_set,
        "data": [item.identifier for item in experiment.data_requirements],
        "capabilities": [item.identifier for item in experiment.capability_requirements],
        "split_spec": experiment.split_spec,
        "evaluation_spec": experiment.evaluation_spec,
        "decision_policy": experiment.decision_policy,
        "budget": {
            "maximum_trials": experiment.maximum_trials,
            "maximum_runtime_minutes": experiment.maximum_runtime_minutes,
            "maximum_compute_cost": experiment.maximum_compute_cost,
        },
    }


def render_plan(payload: dict[str, Any]) -> str:
    lines = [
        f"{payload['id']}: {payload['title']}",
        f"Status: {payload['status']}",
        f"Why next: {payload['why_next']}",
        f"Hypothesis: {payload['hypothesis']}",
        "Rationale:",
    ]
    lines.extend(f"- {item}" for item in payload["rationale"])
    lines.extend(
        [
            f"Expected effect: {payload['expected_effect']}",
            "Falsified when:",
            *(f"- {item}" for item in payload["falsification"]),
            f"Model: {payload['candidate_model']}",
            f"Feature set: {payload['feature_set']}",
            f"Evaluation: {payload['evaluation_spec']}",
            f"Maximum trials: {payload['budget']['maximum_trials']}",
        ]
    )
    return "\n".join(lines) + "\n"


def _experiment_state(
    root: Path, experiment: ExperimentSpec
) -> tuple[list[tuple[str, str]], str, str]:
    temporal_runs = []
    for path in (
        sorted((root / "runs").glob("*/temporal-stability.json"))
        if (root / "runs").is_dir()
        else ()
    ):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("experiment_id") == experiment.identifier:
            temporal_runs.append(path)

    if experiment.evaluation_spec == "EVALUATION-TEMPORAL-STABILITY-0001":
        if temporal_runs:
            rel = temporal_runs[-1].relative_to(root).as_posix()
            return (
                [("temporal stability", f"complete ({rel})")],
                "temporal-stability-complete",
                "Review the completed temporal evidence and commit the next governed research step.",
            )
        return (
            [("temporal stability", "pending")],
            "temporal-stability-pending",
            f"Run the committed temporal-stability protocol for {experiment.identifier}.",
        )
    return (
        [("evaluation", "advanced workflow required")],
        "advanced",
        "Use the advanced experiment commands for the committed evaluation protocol.",
    )
