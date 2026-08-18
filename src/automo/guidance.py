"""Minimal agent-facing research guidance with project-owned extensions."""

from __future__ import annotations

import fnmatch
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from pathlib import Path, PurePosixPath


class GuidanceError(RuntimeError):
    pass


_CORE = (
    "workflows/research-iteration.md",
    "standards/research.md",
    "standards/evidence.md",
    "acceptance/core.md",
)
_TASKS = {
    "hypothesis-planning": (
        "workflows/hypothesis-planning.md",
        "policies/bounded-search.md",
        "policies/multiple-testing.md",
        "policies/early-stopping.md",
    ),
    "experiment-design": (
        "workflows/experiment-design.md",
        "standards/leakage.md",
        "policies/sealed-oos.md",
        "policies/multiple-testing.md",
        "policies/early-stopping.md",
        "acceptance/candidate-admission.md",
        "acceptance/agent-adherence.md",
    ),
    "model-diagnosis": (
        "workflows/model-diagnosis.md",
        "standards/diagnosis.md",
        "references/diagnosis-patterns.md",
        "references/intervention-decision-table.md",
        "standards/model-comparison.md",
    ),
    "feature-research": (
        "workflows/feature-research.md",
        "policies/bounded-search.md",
        "policies/multiple-testing.md",
        "acceptance/candidate-admission.md",
        "acceptance/agent-adherence.md",
    ),
    "calibration-research": (
        "workflows/calibration-research.md",
        "standards/model-comparison.md",
        "policies/sealed-oos.md",
        "policies/multiple-testing.md",
        "acceptance/agent-adherence.md",
    ),
    "meta-model-research": (
        "workflows/meta-model-research.md",
        "standards/leakage.md",
        "policies/sealed-oos.md",
        "policies/multiple-testing.md",
        "references/meta-model-patterns.md",
        "acceptance/agent-adherence.md",
    ),
    "refresh-analysis": (
        "workflows/refresh-analysis.md",
        "standards/diagnosis.md",
        "references/diagnosis-patterns.md",
        "references/intervention-decision-table.md",
        "standards/model-comparison.md",
    ),
    "hypothesis-conclusion": (
        "workflows/hypothesis-conclusion.md",
        "policies/multiple-testing.md",
        "policies/early-stopping.md",
        "acceptance/research-completion.md",
        "acceptance/agent-adherence.md",
    ),
    "capability-handoff": (
        "workflows/capability-handoff.md",
        "policies/capability-escalation.md",
        "contracts/getdone-handoff.md",
    ),
}
_MAX_SELECTED_DOCUMENTS = 16
_REQUIRED_TASK_DOCUMENTS = {key: (values[0],) for key, values in _TASKS.items()}
_PROJECT_AGENT_SCHEMA_VERSION = 1
_LOCK_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class GuidanceDocument:
    path: str
    content: str
    source: str = "builtin"


def task_classes() -> tuple[str, ...]:
    return tuple(_TASKS)


def _safe_project_path(value: str) -> PurePosixPath:
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise GuidanceError(f"unsafe .project-agent guidance path: {value}")
    return candidate


def _load_project_agent(
    root: Path, concerns: Sequence[str], changed_paths: Sequence[str] = ()
) -> tuple[GuidanceDocument, ...]:
    base = root / ".project-agent" / "automo"
    index_path = base / "index.json"
    if not index_path.is_file():
        return ()
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuidanceError(f"cannot read .project-agent/automo/index.json: {exc}") from exc
    if not isinstance(index, dict) or index.get("schema_version") != _PROJECT_AGENT_SCHEMA_VERSION:
        raise GuidanceError(
            f"unsupported .project-agent/automo index schema; expected {_PROJECT_AGENT_SCHEMA_VERSION}"
        )
    selected: list[GuidanceDocument] = []
    baseline = base / "AGENTS.md"
    if not baseline.is_file():
        raise GuidanceError(
            ".project-agent/automo/AGENTS.md is required when .project-agent/automo exists"
        )
    selected.append(
        GuidanceDocument(
            ".project-agent/automo/AGENTS.md", baseline.read_text(encoding="utf-8"), "project-agent"
        )
    )
    requested = set(concerns)
    inferred: set[str] = set()
    infer = index.get("infer", [])
    if not isinstance(infer, list):
        raise GuidanceError(".project-agent/automo/index.json infer must be a list")
    for position, item in enumerate(infer):
        if not isinstance(item, dict):
            raise GuidanceError(f".project-agent infer[{position}] must be an object")
        patterns = item.get("paths", [])
        inferred_concerns = item.get("concerns", [])
        if not isinstance(patterns, list) or not all(isinstance(x, str) and x for x in patterns):
            raise GuidanceError(f".project-agent infer[{position}].paths must be non-empty strings")
        if not isinstance(inferred_concerns, list) or not all(
            isinstance(x, str) and x for x in inferred_concerns
        ):
            raise GuidanceError(
                f".project-agent infer[{position}].concerns must be non-empty strings"
            )
        if any(
            any(
                fnmatch.fnmatch(path.replace("\\", "/").removeprefix("./"), pattern)
                for pattern in patterns
            )
            for path in changed_paths
        ):
            inferred.update(inferred_concerns)
    requested.update(inferred)
    rules = index.get("rules", [])
    if not isinstance(rules, list):
        raise GuidanceError(".project-agent/automo/index.json rules must be a list")
    seen_paths: set[str] = set()
    seen_rule_ids: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise GuidanceError(".project-agent rule must be an object")
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            raise GuidanceError(".project-agent rule id must be a non-empty string")
        if rule_id in seen_rule_ids:
            raise GuidanceError(f"duplicate .project-agent rule id: {rule_id}")
        seen_rule_ids.add(rule_id)
        rule_concerns = rule.get("concerns", [])
        rule_paths = rule.get("paths", [])
        loads = rule.get("load", [])
        if not isinstance(rule_concerns, list) or not all(
            isinstance(x, str) and x for x in rule_concerns
        ):
            raise GuidanceError(".project-agent rule concerns must be strings")
        if not isinstance(rule_paths, list) or not all(
            isinstance(x, str) and x for x in rule_paths
        ):
            raise GuidanceError(".project-agent rule paths must be strings")
        if not rule_concerns and not rule_paths:
            raise GuidanceError(f".project-agent rule {rule_id} needs concerns or paths")
        path_match = any(
            any(
                fnmatch.fnmatch(path.replace("\\", "/").removeprefix("./"), pattern)
                for pattern in rule_paths
            )
            for path in changed_paths
        )
        if not requested.intersection(rule_concerns) and not path_match:
            continue
        if not isinstance(loads, list) or not all(isinstance(x, str) for x in loads):
            raise GuidanceError(".project-agent rule load must be strings")
        for raw in loads:
            rel = _safe_project_path(raw)
            path = base.joinpath(*rel.parts)
            try:
                resolved = path.resolve()
                resolved.relative_to(base.resolve())
            except ValueError as exc:
                raise GuidanceError(
                    f"project-agent guidance escapes project directory: {raw}"
                ) from exc
            if not path.is_file():
                raise GuidanceError(f"project-agent guidance file is missing: {raw}")
            display = f".project-agent/automo/{rel.as_posix()}"
            if display in seen_paths:
                continue
            seen_paths.add(display)
            selected.append(
                GuidanceDocument(display, path.read_text(encoding="utf-8"), "project-agent")
            )
    return tuple(selected)


def select_guidance(
    task_class: str,
    *,
    project_root: Path | None = None,
    concerns: Sequence[str] = (),
    changed_paths: Sequence[str] = (),
    use_project_agent: bool = True,
) -> tuple[GuidanceDocument, ...]:
    if task_class not in _TASKS:
        expected = ", ".join(_TASKS)
        raise GuidanceError(
            f"unknown research task class: {task_class}; expected one of {expected}"
        )
    paths: list[str] = []
    for path in (*_CORE, *_TASKS[task_class]):
        if path not in paths:
            paths.append(path)
    root = files("automo.skill")
    docs = [
        GuidanceDocument(path, root.joinpath(path).read_text(encoding="utf-8")) for path in paths
    ]
    if use_project_agent and project_root is not None:
        project_concerns = (task_class, *concerns)
        docs.extend(_load_project_agent(project_root.resolve(), project_concerns, changed_paths))
    if len(docs) > _MAX_SELECTED_DOCUMENTS:
        raise GuidanceError(
            f"guidance selection has {len(docs)} documents; maximum is {_MAX_SELECTED_DOCUMENTS}"
        )
    return tuple(docs)


def render_guidance(
    documents: Iterable[GuidanceDocument], *, paths_only: bool = False, explain: bool = False
) -> str:
    docs = tuple(documents)
    if paths_only:
        return "\n".join(doc.path for doc in docs) + "\n"
    chunks = []
    if explain:
        chunks.append(
            "# Automo guidance composition\n"
            + "\n".join(f"- [{doc.source}] {doc.path}" for doc in docs)
            + "\n"
        )
    for doc in docs:
        chunks.append(
            f"<!-- automo-guidance: {doc.source}:{doc.path} -->\n{doc.content.rstrip()}\n"
        )
    return "\n".join(chunks)


def _digest_entries(entries: Sequence[tuple[str, bytes]]) -> str:
    digest = sha256()
    for path, content in sorted(entries):
        digest.update(path.encode())
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def guidance_composition(root: Path) -> dict[str, object]:
    builtin_entries: list[tuple[str, bytes]] = []
    for task in task_classes():
        for doc in select_guidance(task, use_project_agent=False):
            if not any(path == doc.path for path, _ in builtin_entries):
                builtin_entries.append((doc.path, doc.content.encode()))
    project_entries: list[tuple[str, bytes]] = []
    project_root = root / ".project-agent" / "automo"
    if project_root.is_dir():
        for path in sorted(project_root.rglob("*")):
            if path.is_file():
                project_entries.append((path.relative_to(root).as_posix(), path.read_bytes()))
    from automo import __version__

    builtin_digest = _digest_entries(builtin_entries)
    project_digest = _digest_entries(project_entries) if project_entries else None
    composition_digest = _digest_entries(
        [("builtin", builtin_digest.encode()), ("project-agent", (project_digest or "").encode())]
    )
    return {
        "artifact_type": "automo.guidance_lock",
        "schema_version": _LOCK_SCHEMA_VERSION,
        "automo_version": __version__,
        "builtin_guidance_digest": builtin_digest,
        "project_agent_digest": project_digest,
        "composition_digest": composition_digest,
    }


def guidance_lock(root: Path, *, write: bool = False) -> tuple[str, dict[str, object]]:
    current = guidance_composition(root.resolve())
    path = root.resolve() / ".automo" / "guidance.lock.json"
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return "written", current
    if not path.is_file():
        return "missing", current
    try:
        locked = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuidanceError(f"cannot read guidance lock: {exc}") from exc
    if locked == current:
        return "current", current
    if locked.get("automo_version") != current["automo_version"]:
        return "version-change", current
    return "drift", current


def validate_project_agent(root: Path) -> tuple[str, ...]:
    errors: list[str] = []
    base = root / ".project-agent" / "automo"
    if not base.exists():
        return ()
    try:
        # Every rule is parsed and every referenced file checked by selecting its concerns.
        index = json.loads((base / "index.json").read_text(encoding="utf-8"))
        concerns = sorted(
            {
                c
                for r in index.get("rules", [])
                if isinstance(r, dict)
                for c in r.get("concerns", [])
                if isinstance(c, str)
            }
        )
        if index.get("schema_version") != _PROJECT_AGENT_SCHEMA_VERSION:
            raise GuidanceError("unsupported .project-agent/automo index schema")
        _load_project_agent(root, concerns, ())
    except (OSError, json.JSONDecodeError, GuidanceError) as exc:
        errors.append(str(exc))
    return tuple(errors)


def validate_guidance_pack() -> tuple[str, ...]:
    errors: list[str] = []
    for task_class in task_classes():
        try:
            docs = select_guidance(task_class, use_project_agent=False)
        except Exception as exc:
            errors.append(f"{task_class}: selection failed: {exc}")
            continue
        if len(docs) > _MAX_SELECTED_DOCUMENTS:
            errors.append(
                f"{task_class}: selects {len(docs)} documents; maximum is {_MAX_SELECTED_DOCUMENTS}"
            )
        paths = {doc.path for doc in docs}
        for required in _REQUIRED_TASK_DOCUMENTS[task_class]:
            if required not in paths:
                errors.append(f"{task_class}: missing required guidance {required}")
        for doc in docs:
            if not doc.content.strip():
                errors.append(f"{task_class}: empty guidance document {doc.path}")
            if not doc.content.lstrip().startswith("# "):
                errors.append(f"{task_class}: guidance document lacks title heading {doc.path}")
    return tuple(errors)
