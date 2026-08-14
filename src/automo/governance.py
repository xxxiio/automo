"""Project-owned research governance under ``.automo``."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class GovernanceError(RuntimeError):
    pass


STATE_SCHEMA_VERSION = 1


class MilestoneStatus(StrEnum):
    PROPOSED = "proposed"
    PLANNING = "planning"
    APPROVED = "approved"
    ACTIVE = "active"
    CONCLUDED = "concluded"


class MilestoneOutcome(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"
    INVALID = "invalid"


_ALLOWED = {
    MilestoneStatus.PROPOSED: {MilestoneStatus.PLANNING},
    MilestoneStatus.PLANNING: {MilestoneStatus.APPROVED},
    MilestoneStatus.APPROVED: {MilestoneStatus.ACTIVE},
    MilestoneStatus.ACTIVE: {MilestoneStatus.CONCLUDED},
    MilestoneStatus.CONCLUDED: set(),
}


@dataclass(frozen=True)
class ResearchMilestone:
    id: str
    question: str
    why_next: str
    status: MilestoneStatus
    exit_criteria: tuple[str, ...]
    non_goals: tuple[str, ...] = ()
    outcome: MilestoneOutcome | None = None
    conclusion: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": "automo.research_milestone",
            "schema_version": 1,
            "id": self.id,
            "question": self.question,
            "why_next": self.why_next,
            "status": self.status.value,
            "exit_criteria": list(self.exit_criteria),
            "non_goals": list(self.non_goals),
            "outcome": self.outcome.value if self.outcome else None,
            "conclusion": self.conclusion,
        }


class ResearchGovernance:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.state = self.root / ".automo"
        self.current = self.state / "current"
        self.milestones = self.state / "milestones"

    def initialise(self) -> tuple[Path, ...]:
        created: list[Path] = []
        for path in (self.state, self.current, self.milestones):
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created.append(path.relative_to(self.root))
        defaults = {
            self.state / "project.yaml": {
                "artifact_type": "automo.research_project",
                "schema_version": 1,
                "mode": "plan",
                "current_milestone": None,
            },
            self.state / "roadmap.yaml": {
                "artifact_type": "automo.research_roadmap",
                "schema_version": 1,
                "milestones": [],
            },
            self.current / "plan.yaml": {
                "artifact_type": "automo.research_plan_state",
                "schema_version": 1,
                "mode": "plan",
                "milestone_id": None,
                "execution_allowed": False,
                "planning_questions": [
                    "What is the highest-value unresolved research question?",
                    "What evidence would falsify or conclude it?",
                    "What data, split, capability, and OOS budgets must be committed?",
                ],
            },
            self.current / "next-step.yaml": {
                "artifact_type": "automo.research_next_step",
                "schema_version": 1,
                "kind": "plan-milestone",
                "objective": "Define and approve the first bounded research milestone.",
            },
        }
        for path, payload in defaults.items():
            if not path.exists():
                _write_yaml(path, payload)
                created.append(path.relative_to(self.root))
        return tuple(created)

    def create_milestone(
        self, identifier: str, *, question: str, why_next: str,
        exit_criteria: tuple[str, ...], non_goals: tuple[str, ...] = (),
    ) -> ResearchMilestone:
        if not exit_criteria:
            raise GovernanceError("research milestone requires at least one exit criterion")
        self.initialise()
        path = self.milestones / f"{identifier}.yaml"
        if path.exists():
            raise GovernanceError(f"research milestone already exists: {identifier}")
        milestone = ResearchMilestone(identifier, question, why_next, MilestoneStatus.PROPOSED, exit_criteria, non_goals)
        _write_yaml(path, milestone.as_dict())
        roadmap = _load_yaml(self.state / "roadmap.yaml")
        roadmap.setdefault("milestones", []).append(identifier)
        _write_yaml(self.state / "roadmap.yaml", roadmap)
        self._set_current(milestone)
        return milestone

    def load(self, identifier: str) -> ResearchMilestone:
        path = self.milestones / f"{identifier}.yaml"
        if not path.is_file():
            raise GovernanceError(f"unknown research milestone: {identifier}")
        raw = _load_yaml(path)
        try:
            return ResearchMilestone(
                id=str(raw["id"]), question=str(raw["question"]), why_next=str(raw["why_next"]),
                status=MilestoneStatus(raw["status"]), exit_criteria=tuple(raw.get("exit_criteria", ())),
                non_goals=tuple(raw.get("non_goals", ())),
                outcome=MilestoneOutcome(raw["outcome"]) if raw.get("outcome") else None,
                conclusion=raw.get("conclusion"),
            )
        except (KeyError, ValueError) as exc:
            raise GovernanceError(f"invalid research milestone contract: {path}") from exc

    def current_milestone(self) -> ResearchMilestone | None:
        project = _load_yaml(self.state / "project.yaml") if (self.state / "project.yaml").is_file() else {}
        identifier = project.get("current_milestone")
        return self.load(str(identifier)) if identifier else None

    def transition(self, identifier: str, target: MilestoneStatus) -> ResearchMilestone:
        milestone = self.load(identifier)
        if target not in _ALLOWED[milestone.status]:
            raise GovernanceError(f"illegal research milestone transition: {milestone.status.value} -> {target.value}")
        updated = ResearchMilestone(
            milestone.id, milestone.question, milestone.why_next, target,
            milestone.exit_criteria, milestone.non_goals, milestone.outcome, milestone.conclusion,
        )
        _write_yaml(self.milestones / f"{identifier}.yaml", updated.as_dict())
        self._set_current(updated)
        return updated

    def conclude(self, identifier: str, *, outcome: MilestoneOutcome, conclusion: str) -> ResearchMilestone:
        milestone = self.load(identifier)
        if milestone.status != MilestoneStatus.ACTIVE:
            raise GovernanceError("only an active research milestone can be concluded")
        updated = ResearchMilestone(
            milestone.id, milestone.question, milestone.why_next, MilestoneStatus.CONCLUDED,
            milestone.exit_criteria, milestone.non_goals, outcome, conclusion,
        )
        _write_yaml(self.milestones / f"{identifier}.yaml", updated.as_dict())
        project = _load_yaml(self.state / "project.yaml")
        project["mode"] = "plan"
        project["current_milestone"] = None
        _write_yaml(self.state / "project.yaml", project)
        _write_yaml(self.current / "plan.yaml", {
            "artifact_type": "automo.research_plan_state", "schema_version": 1,
            "mode": "plan", "milestone_id": None, "execution_allowed": False,
            "planning_questions": ["Select the highest-priority next research question."],
        })
        _write_yaml(self.current / "next-step.yaml", {
            "artifact_type": "automo.research_next_step", "schema_version": 1,
            "kind": "plan-milestone", "objective": "Select the highest-priority next research question.",
        })
        (self.current / "milestone.yaml").unlink(missing_ok=True)
        return updated

    def require_execution_ready(self) -> ResearchMilestone | None:
        if not (self.state / "project.yaml").is_file():
            return None  # backwards-compatible projects not yet using governance
        milestone = self.current_milestone()
        if milestone is None:
            raise GovernanceError("research project is in plan mode; approve and activate a milestone before executing research")
        if milestone.status != MilestoneStatus.ACTIVE:
            raise GovernanceError(f"research milestone {milestone.id} is {milestone.status.value}; activate it before executing research")
        return milestone

    def status_payload(self) -> dict[str, Any]:
        self.initialise()
        project = _load_yaml(self.state / "project.yaml")
        milestone = self.current_milestone()
        next_step = _load_yaml(self.current / "next-step.yaml")
        return {
            "mode": project.get("mode", "plan"),
            "current_milestone": milestone.as_dict() if milestone else None,
            "next_step": next_step,
        }

    def plan_payload(self) -> dict[str, Any]:
        payload = self.status_payload()
        milestone = payload["current_milestone"]
        return {
            "mode": payload["mode"],
            "milestone": milestone,
            "next_step": payload["next_step"],
            "execution_allowed": bool(milestone and milestone.get("status") == "active"),
        }

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.state.exists():
            return ()
        for required in (self.state / "project.yaml", self.state / "roadmap.yaml", self.current / "plan.yaml", self.current / "next-step.yaml"):
            if not required.is_file():
                errors.append(f"missing Automo research-state contract: {required.relative_to(self.root)}")
        if errors:
            return tuple(errors)
        expected = {
            self.state / "project.yaml": "automo.research_project",
            self.state / "roadmap.yaml": "automo.research_roadmap",
            self.current / "plan.yaml": "automo.research_plan_state",
            self.current / "next-step.yaml": "automo.research_next_step",
        }
        for path, artifact_type in expected.items():
            raw = _load_yaml(path)
            if raw.get("artifact_type") != artifact_type:
                errors.append(f"{path.relative_to(self.root)} has wrong artifact_type")
            if raw.get("schema_version") != STATE_SCHEMA_VERSION:
                errors.append(
                    f"{path.relative_to(self.root)} schema_version must be {STATE_SCHEMA_VERSION}; "
                    "explicit migration is required"
                )
        for path in sorted(self.milestones.glob("*.yaml")):
            raw = _load_yaml(path)
            if raw.get("artifact_type") != "automo.research_milestone" or raw.get("schema_version") != STATE_SCHEMA_VERSION:
                errors.append(f"{path.relative_to(self.root)} uses an unsupported research-state schema")
        if errors:
            return tuple(errors)
        try:
            current = self.current_milestone()
            project = _load_yaml(self.state / "project.yaml")
            mode = project.get("mode")
            if mode not in {"plan", "research"}:
                errors.append(".automo/project.yaml mode must be 'plan' or 'research'")
            if current and current.status == MilestoneStatus.ACTIVE and mode != "research":
                errors.append("active research milestone requires project mode 'research'")
            if current and current.status != MilestoneStatus.ACTIVE and mode != "plan":
                errors.append("non-active research milestone requires project mode 'plan'")
        except GovernanceError as exc:
            errors.append(str(exc))
        return tuple(errors)

    def _set_current(self, milestone: ResearchMilestone) -> None:
        project = _load_yaml(self.state / "project.yaml")
        project["current_milestone"] = milestone.id
        project["mode"] = "research" if milestone.status == MilestoneStatus.ACTIVE else "plan"
        _write_yaml(self.state / "project.yaml", project)
        _write_yaml(self.current / "milestone.yaml", milestone.as_dict())
        _write_yaml(self.current / "plan.yaml", {
            "artifact_type": "automo.research_plan_state",
            "schema_version": 1,
            "mode": project["mode"],
            "milestone_id": milestone.id,
            "question": milestone.question,
            "why_next": milestone.why_next,
            "exit_criteria": list(milestone.exit_criteria),
            "non_goals": list(milestone.non_goals),
            "execution_allowed": milestone.status == MilestoneStatus.ACTIVE,
        })
        action = {
            MilestoneStatus.PROPOSED: "Review the proposed milestone and enter planning.",
            MilestoneStatus.PLANNING: "Complete the bounded research plan and approve the milestone.",
            MilestoneStatus.APPROVED: "Activate the approved milestone before executing experiments.",
            MilestoneStatus.ACTIVE: "Execute exactly the next committed bounded research step.",
            MilestoneStatus.CONCLUDED: "Plan the next research milestone.",
        }[milestone.status]
        _write_yaml(self.current / "next-step.yaml", {
            "artifact_type": "automo.research_next_step", "schema_version": 1,
            "kind": "milestone-transition", "milestone_id": milestone.id, "objective": action,
        })


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise GovernanceError(f"cannot read research-state contract: {path}") from exc
    if not isinstance(value, dict):
        raise GovernanceError(f"research-state contract must be a mapping: {path}")
    return value


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
