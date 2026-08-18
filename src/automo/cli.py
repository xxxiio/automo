"""Automo command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from automo.capabilities import (
    CapabilityLifecycleError,
    create_getdone_handoff,
    fulfill_capability,
    inspect_capability,
)
from automo.contracts import ContractError
from automo.decisions import DecisionError, decide_local_run
from automo.execution import (
    evaluate_local_out_of_sample,
    prepare_local_experiment,
    run_local_experiment,
    run_temporal_stability,
)
from automo.execution.local import ExecutionError
from automo.features import FeatureDispositionError, dispose_local_features
from automo.findings import FindingError, propose_next_experiment
from automo.governance import (
    CandidateInput,
    EvaluationDepth,
    GovernanceError,
    HypothesisObjective,
    HypothesisStatus,
    ModelRelationKind,
    ModelRole,
    ObjectiveDirection,
    ObjectiveLevel,
    ResearchGovernance,
)
from automo.guidance import (
    GuidanceError,
    guidance_lock,
    render_guidance,
    select_guidance,
    task_classes,
    validate_project_agent,
)
from automo.integrations.getdone import GetDoneCapabilityWorkflow
from automo.prerequisites import (
    DataAvailability,
    MappingDataCatalogue,
    SetCapabilityCatalogue,
    validate_prerequisites,
)
from automo.project import ResearchProject
from automo.promotions import PromotionError, recommend_promotion
from automo.refresh import DataIteration, FilesystemPoolStore, RefreshError, RefreshService
from automo.registry import FilesystemModelRegistry, ModelStatus, RegistryError
from automo.research import (
    FilesystemResearchStore,
    ResearchBudget,
    ResearchError,
    ResearchSafeguards,
    ResearchService,
)
from automo.runtime import ResearchRuntime, load_project_plugin
from automo.ux import (
    doctor_checks,
    initialise_mr_project,
    package_version,
    plan_payload,
    project_status,
    render_plan,
    render_status,
    run_next_transition,
)
from automo.ux import (
    validate_project as validate_mr_project,
)

app = typer.Typer(
    name="automo",
    no_args_is_help=True,
    add_completion=False,
    suggest_commands=True,
    help="Deterministic, evidence-driven model-research workflows.",
)
experiment_app = typer.Typer(help="Advanced experiment-stage commands.", no_args_is_help=True)
features_app = typer.Typer(help="Advanced feature-analysis commands.", no_args_is_help=True)
findings_app = typer.Typer(help="Advanced findings commands.", no_args_is_help=True)
stability_app = typer.Typer(help="Advanced temporal-stability commands.", no_args_is_help=True)
promotion_app = typer.Typer(help="Advanced promotion commands.", no_args_is_help=True)
capability_app = typer.Typer(help="Capability request lifecycle.", no_args_is_help=True)
integration_app = typer.Typer(help="Optional workflow integrations.", no_args_is_help=True)
models_app = typer.Typer(
    help="Inspect and manage registered model lifecycle state.", no_args_is_help=True
)
refresh_app = typer.Typer(
    help="Refresh retained models against a new immutable data iteration.",
    invoke_without_command=True,
)
research_app = typer.Typer(
    help="Plan and execute bounded automated research.", no_args_is_help=True
)
app.add_typer(experiment_app, name="experiment")
app.add_typer(features_app, name="features")
app.add_typer(findings_app, name="findings")
app.add_typer(stability_app, name="stability")
app.add_typer(promotion_app, name="promotion")
app.add_typer(capability_app, name="capability")
app.add_typer(integration_app, name="integration")
app.add_typer(models_app, name="models")
app.add_typer(refresh_app, name="refresh")
app.add_typer(research_app, name="research")


def _root_option() -> Path:
    return Path.cwd()


def _refresh_components(root: Path, pool_id: str, data_source_id: str, split_id: str):
    plugin = load_project_plugin(root)
    runtime = ResearchRuntime(plugin)
    pools = {item.id: item for item in plugin.model_pools}
    splits = {item.id: item for item in plugin.split_strategies}
    try:
        pool = pools[pool_id]
    except KeyError as exc:
        raise RefreshError(f"unknown model pool: {pool_id}") from exc
    try:
        split = splits[split_id]
    except KeyError as exc:
        raise RefreshError(f"unknown split strategy: {split_id}") from exc
    if data_source_id not in runtime.data_sources:
        raise RefreshError(f"unknown data source: {data_source_id}")
    registry = FilesystemModelRegistry(root / ".automo" / "registry")
    for runner in plugin.model_runners:
        codec = getattr(runner, "artifact_codec", None)
        if codec is not None:
            registry.register_codec(codec)
    for calibrator in plugin.calibrators:
        codec = getattr(calibrator, "artifact_codec", None)
        if codec is not None:
            registry.calibration_codecs[codec.id] = codec
    return runtime, pool, split, registry


def _research_components(root: Path, space_id: str):
    plugin = load_project_plugin(root)
    runtime = ResearchRuntime(plugin)
    spaces = {item.id: item for item in plugin.research_spaces}
    try:
        space = spaces[space_id]
    except KeyError as exc:
        raise ResearchError(f"unknown research search space: {space_id}") from exc
    registry = FilesystemModelRegistry(root / ".automo" / "registry")
    for runner in plugin.model_runners:
        codec = getattr(runner, "artifact_codec", None)
        if codec is not None:
            registry.register_codec(codec)
    store = FilesystemResearchStore(root / ".automo" / "research")
    service = ResearchService(
        runtime, split_strategies=plugin.split_strategies, store=store, registry=registry
    )
    return runtime, space, store, service


@research_app.command("plan")
def research_plan(
    iteration: str,
    baseline: Annotated[str, typer.Option("--baseline", help="Baseline model spec id.")],
    data_source: Annotated[str, typer.Option("--data-source", help="Configured data source id.")],
    split: Annotated[str, typer.Option("--split", help="Configured split strategy id.")],
    space: Annotated[str, typer.Option("--space", help="Configured research search-space id.")],
    diagnosis: Annotated[str, typer.Option("--diagnosis", help="Structured current diagnosis.")],
    maximum_candidates: Annotated[int, typer.Option("--maximum-candidates")] = 8,
    maximum_oos_candidates: Annotated[int, typer.Option("--maximum-oos-candidates")] = 2,
    minimum_improvement: Annotated[float, typer.Option("--minimum-improvement")] = 0.0,
    finding: Annotated[list[str] | None, typer.Option("--finding")] = None,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    try:
        governance = ResearchGovernance(root)
        provenance = (
            governance.provenance(iteration)
            if (root / ".automo" / "project.yaml").is_file()
            else None
        )
        _, search_space, _, service = _research_components(root, space)
        plan = service.plan(
            iteration_id=iteration,
            baseline_model_spec_id=baseline,
            data_source_id=data_source,
            split_strategy_id=split,
            diagnosis=diagnosis,
            findings=tuple(finding or ()),
            search_space=search_space,
            budget=ResearchBudget(
                maximum_candidates=maximum_candidates,
                maximum_model_fits=max(maximum_candidates + 1, 2),
                maximum_oos_candidates=maximum_oos_candidates,
            ),
            safeguards=ResearchSafeguards(minimum_improvement=minimum_improvement),
            provenance=provenance,
        )
    except Exception as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Research iteration: {plan.id}")
    typer.echo(f"Diagnosis: {plan.diagnosis}")
    typer.echo(f"Candidates: {len(plan.candidates)}")
    for candidate in plan.candidates:
        typer.echo(
            f"- {candidate.id}: {candidate.intervention.kind.value} {dict(candidate.intervention.values)}"
        )


@research_app.command("run")
def research_run(
    iteration: str,
    space: Annotated[str, typer.Option("--space", help="Configured research search-space id.")],
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    try:
        ResearchGovernance(root).require_execution_ready()
        _, _, store, service = _research_components(root, space)
        report = service.execute(store.load_plan(iteration))
    except Exception as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Research iteration: {report.id}")
    typer.echo(f"Validation trials: {report.validation_trials}")
    typer.echo(f"Sealed OOS trials: {report.oos_trials}")
    for result in report.results:
        typer.echo(f"- {result.candidate_id}: {result.stage.value} {result.reason}")


@research_app.command("status")
def research_status(
    iteration: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    directory = root / ".automo" / "research" / iteration
    plan = directory / "plan.json"
    report = directory / "report.json"
    if not plan.is_file():
        raise typer.Exit(_error(f"unknown research iteration: {iteration}"))
    typer.echo(f"{iteration}: {'completed' if report.is_file() else 'planned'}")


@research_app.command("history")
def research_history(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    store = FilesystemResearchStore(root / ".automo" / "research")
    for path in store.history():
        payload = json.loads(path.read_text(encoding="utf-8"))
        typer.echo(
            f"{path.parent.name} validation={payload.get('validation_trials', 0)} oos={payload.get('oos_trials', 0)}"
        )


@research_app.command("show")
def research_show(
    iteration: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    directory = root / ".automo" / "research" / iteration
    path = (
        directory / "report.json"
        if (directory / "report.json").is_file()
        else directory / "plan.json"
    )
    if not path.is_file():
        raise typer.Exit(_error(f"unknown research iteration: {iteration}"))
    typer.echo(path.read_text(encoding="utf-8"), nl=False)


@research_app.command("candidates")
def research_candidates(
    iteration: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    path = root / ".automo" / "research" / iteration / "plan.json"
    if not path.is_file():
        raise typer.Exit(_error(f"unknown research iteration: {iteration}"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    for item in payload.get("candidates", []):
        typer.echo(
            f"{item['id']} {item['intervention']['kind']} {item['intervention']['values']} fingerprint={item['fingerprint'][:12]}"
        )


@refresh_app.callback(invoke_without_command=True)
def refresh_command(
    ctx: typer.Context,
    pool: Annotated[str | None, typer.Option("--pool", help="Configured model pool id.")] = None,
    data_source: Annotated[
        str | None, typer.Option("--data-source", help="Configured data source id.")
    ] = None,
    split: Annotated[
        str | None, typer.Option("--split", help="Configured split strategy id.")
    ] = None,
    iteration: Annotated[
        str | None, typer.Option("--iteration", help="Immutable data iteration id.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Plan without fitting or persisting refresh state.")
    ] = False,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if not all((pool, data_source, split, iteration)):
        raise typer.BadParameter("--pool, --data-source, --split and --iteration are required")
    try:
        runtime, pool_spec, split_spec, registry = _refresh_components(
            root, pool, data_source, split
        )
        snapshot = runtime.data_sources[data_source].snapshot()
        data_iteration = DataIteration(iteration, snapshot.id, snapshot.content_hash)
        service = RefreshService(
            runtime,
            registry,
            FilesystemPoolStore(root / ".automo" / "pools"),
            calibrators=runtime.plugin.calibrators,
            selectors=runtime.plugin.model_selectors,
            refresh_root=root / ".automo" / "refresh",
        )
        result = service.run(
            pool_spec, data_iteration, split_spec, data_source_id=data_source, dry_run=dry_run
        )
    except Exception as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(json.dumps(result, indent=2, sort_keys=True, default=str))


@refresh_app.command("history")
def refresh_history(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    refresh_root = root / ".automo" / "refresh"
    if not refresh_root.is_dir():
        return
    for path in sorted(refresh_root.glob("*/report.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        typer.echo(
            f"{path.parent.name}  retained={','.join(payload.get('retained_model_ids', []))}"
        )


@refresh_app.command("show")
def refresh_show(
    iteration: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    path = root / ".automo" / "refresh" / iteration / "report.json"
    if not path.is_file():
        raise typer.Exit(_error(f"unknown refresh iteration: {iteration}"))
    typer.echo(path.read_text(encoding="utf-8"), nl=False)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(package_version())
        raise typer.Exit()


@app.callback()
def root_callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the installed Automo version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Run Automo through one discoverable command tree."""
    del version


def _root_option() -> Path:
    return Path.cwd()


@app.command("guidance")
def guidance_command(
    task_class: Annotated[str, typer.Option("--task-class", help="Research task class.")],
    concern: Annotated[
        list[str] | None,
        typer.Option("--concern", help="Project-defined concern; repeat as needed."),
    ] = None,
    changed_path: Annotated[
        list[str] | None,
        typer.Option("--changed-path", help="Relevant project path; repeat for inference."),
    ] = None,
    no_project_agent: Annotated[
        bool, typer.Option("--no-project-agent", help="Disable .project-agent/automo discovery.")
    ] = False,
    paths_only: Annotated[
        bool, typer.Option("--paths-only", help="Emit selected guidance paths only.")
    ] = False,
    explain: Annotated[
        bool, typer.Option("--explain", help="Show guidance source provenance.")
    ] = False,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Select canonical research guidance plus additive .project-agent/automo rules."""
    try:
        docs = select_guidance(
            task_class,
            project_root=root,
            concerns=tuple(concern or ()),
            changed_paths=tuple(changed_path or ()),
            use_project_agent=not no_project_agent,
        )
        typer.echo(render_guidance(docs, paths_only=paths_only, explain=explain), nl=False)
    except GuidanceError as exc:
        raise typer.Exit(_error(str(exc))) from exc


@app.command("guidance-check")
def guidance_check_command(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Validate project-agent references and the pinned guidance composition."""
    errors = validate_project_agent(root)
    if errors:
        for error in errors:
            typer.echo(f"error: {error}", err=True)
        raise typer.Exit(1)
    try:
        status, _ = guidance_lock(root)
    except GuidanceError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo("project-agent: valid")
    typer.echo(f"guidance-lock: {status}")
    if status not in {"current", "missing"}:
        raise typer.Exit(1)


@app.command("guidance-lock")
def guidance_lock_command(
    write: Annotated[
        bool, typer.Option("--write", help="Write the reviewed current composition lock.")
    ] = False,
    plan: Annotated[bool, typer.Option("--plan", help="Show lock status without writing.")] = False,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Check or explicitly pin the Automo + project-agent guidance composition."""
    del plan
    try:
        status, payload = guidance_lock(root, write=write)
    except GuidanceError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Status: {status}")
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@research_app.command("model-add")
def research_model_add(
    model_id: str,
    role: Annotated[
        str,
        typer.Option(
            "--role", help="standalone, submodel, meta, ensemble, distribution, or decision"
        ),
    ],
    description: Annotated[str, typer.Option("--description")] = "",
    experiment: Annotated[
        str | None, typer.Option("--experiment", help="Experiment that produced this candidate.")
    ] = None,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Register a logical model component in the research model graph."""
    try:
        item = ResearchGovernance(root).register_model(
            model_id, role=ModelRole(role), description=description
        )
    except (GovernanceError, ValueError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Model: {item.id}")
    typer.echo(f"Role: {item.role.value}")


@research_app.command("model-relation-add")
def research_model_relation_add(
    source: str,
    target: str,
    kind: Annotated[
        str, typer.Option("--kind", help="input, correlated, complementary, or alternative")
    ],
    description: Annotated[str, typer.Option("--description")] = "",
    experiment: Annotated[
        str | None, typer.Option("--experiment", help="Experiment that produced this candidate.")
    ] = None,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Add an explicit structural or informational relation between model components."""
    try:
        item = ResearchGovernance(root).add_model_relation(
            source, target, kind=ModelRelationKind(kind), description=description
        )
    except (GovernanceError, ValueError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Relation: {item.source} -> {item.target} ({item.kind.value})")


@research_app.command("candidate-add")
def research_candidate_add(
    candidate_id: str,
    model: Annotated[str, typer.Option("--model")],
    model_spec_id: Annotated[
        str,
        typer.Option(
            "--model-spec-id",
            help="ModelSpec/implementation specification used for this candidate.",
        ),
    ],
    artifact_id: Annotated[
        str,
        typer.Option(
            "--artifact-id", help="Runtime/registry artifact identifier for this candidate."
        ),
    ],
    input_candidate: Annotated[
        list[str] | None,
        typer.Option("--input", help="model:candidate; repeat for composed inputs."),
    ] = None,
    description: Annotated[str, typer.Option("--description")] = "",
    experiment: Annotated[
        str | None, typer.Option("--experiment", help="Experiment that produced this candidate.")
    ] = None,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Register an immutable candidate for one logical model component."""
    try:
        inputs = tuple(_parse_candidate_input(item) for item in (input_candidate or ()))
        governance = ResearchGovernance(root)
        active = governance.current_hypothesis()
        provenance = governance.provenance(experiment) if active is not None else None
        item = governance.register_candidate(
            candidate_id,
            model_id=model,
            model_spec_id=model_spec_id,
            artifact_id=artifact_id,
            inputs=inputs,
            provenance=provenance,
            description=description,
        )
    except GovernanceError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Candidate: {item.id}")
    typer.echo(f"Model: {item.model_id}")


@research_app.command("candidate-select")
def research_candidate_select(
    candidate_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Select the preferred candidate for its logical model component."""
    try:
        item = ResearchGovernance(root).select_candidate(candidate_id)
    except GovernanceError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Selected: {item.id}")
    typer.echo(f"Model: {item.model_id}")


@research_app.command("composition-create")
def research_composition_create(
    experiment_id: str,
    hypothesis: Annotated[str, typer.Option("--hypothesis")],
    target_model: Annotated[str, typer.Option("--target-model")],
    control_candidate: Annotated[str, typer.Option("--control-candidate")],
    treatment_candidate: Annotated[str, typer.Option("--treatment-candidate")],
    metric: Annotated[
        list[str] | None,
        typer.Option("--metric", help="Committed comparison metric; repeat as needed."),
    ] = None,
    rationale: Annotated[str, typer.Option("--rationale")] = "",
    expected_effect: Annotated[str, typer.Option("--expected-effect")] = "",
    falsification: Annotated[
        list[str] | None,
        typer.Option("--falsification", help="Falsification criterion; repeat as needed."),
    ] = None,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Create a controlled comparison between two immutable composed-model candidates."""
    try:
        item = ResearchGovernance(root).create_composition_experiment(
            experiment_id,
            hypothesis_id=hypothesis,
            target_model=target_model,
            control_candidate_id=control_candidate,
            treatment_candidate_id=treatment_candidate,
            metrics=tuple(metric or ()),
            rationale=rationale,
            expected_effect=expected_effect,
            falsification=tuple(falsification or ()),
        )
    except GovernanceError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Composition experiment: {item.id}")
    typer.echo(f"Target model: {item.target_model}")
    typer.echo(f"Kind: {item.kind.value}")


def _parse_candidate_input(raw: str) -> CandidateInput:
    model, separator, candidate = raw.partition(":")
    if not separator or not model or not candidate:
        raise GovernanceError("candidate input must be model:candidate")
    return CandidateInput(model, candidate)


@research_app.command("hypothesis-create")
def research_hypothesis_create(
    hypothesis_id: str,
    statement: Annotated[str, typer.Option("--statement")],
    parent: Annotated[str | None, typer.Option("--parent")] = None,
    primary_model: Annotated[str | None, typer.Option("--primary-model")] = None,
    related_model: Annotated[list[str] | None, typer.Option("--related-model")] = None,
    objective: Annotated[
        list[str] | None,
        typer.Option(
            "--objective", help="metric:level:direction[:required|optional]; repeat as needed"
        ),
    ] = None,
    evaluation_depth: Annotated[
        str, typer.Option("--evaluation-depth", help="validity, local, parent, or system")
    ] = "local",
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Create a falsifiable research hypothesis independent of project milestones."""
    try:
        objectives = []
        for raw in objective or ():
            parts = raw.split(":")
            if len(parts) not in {3, 4}:
                raise GovernanceError(
                    "--objective must be metric:level:direction[:required|optional]"
                )
            required = len(parts) == 3 or parts[3] == "required"
            if len(parts) == 4 and parts[3] not in {"required", "optional"}:
                raise GovernanceError("objective requirement must be required or optional")
            objectives.append(
                HypothesisObjective(
                    metric=parts[0],
                    level=ObjectiveLevel(parts[1]),
                    direction=ObjectiveDirection(parts[2]),
                    required=required,
                )
            )
        item = ResearchGovernance(root).create_hypothesis(
            hypothesis_id,
            statement=statement,
            parent_id=parent,
            primary_model=primary_model,
            related_models=tuple(related_model or ()),
            objectives=tuple(objectives),
            required_evaluation_depth=EvaluationDepth[evaluation_depth.upper()],
        )
    except (GovernanceError, KeyError, ValueError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Hypothesis: {item.id}")
    typer.echo(f"Status: {item.status.value}")


@research_app.command("hypothesis-activate")
def research_hypothesis_activate(
    hypothesis_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Make one unresolved hypothesis the active scientific context for research execution."""
    try:
        item = ResearchGovernance(root).activate_hypothesis(hypothesis_id)
    except GovernanceError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Hypothesis: {item.id}")
    typer.echo("Status: active")


@research_app.command("hypothesis-conclude")
def research_hypothesis_conclude(
    hypothesis_id: str,
    status: Annotated[str, typer.Option("--status", help="supported, rejected, or inconclusive")],
    conclusion: Annotated[str, typer.Option("--conclusion")],
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Record the current conclusion for an active hypothesis."""
    try:
        item = ResearchGovernance(root).conclude_hypothesis(
            hypothesis_id, status=HypothesisStatus(status), conclusion=conclusion
        )
    except (GovernanceError, ValueError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Hypothesis: {item.id}")
    typer.echo(f"Status: {item.status.value}")


@research_app.command("hypothesis-tree")
def research_hypothesis_tree(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Render the scientific hypothesis hierarchy; this is distinct from the model graph."""
    try:
        rows = ResearchGovernance(root).hypothesis_tree()
    except GovernanceError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    for depth, item in rows:
        typer.echo(f"{'  ' * depth}- {item.id} [{item.status.value}] {item.statement}")


@research_app.command("task-classes")
def research_task_classes() -> None:
    """List agent-facing research task classes accepted by ``automo guidance``."""
    for item in task_classes():
        typer.echo(item)


@app.command("init")
def init_command(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Create the standalone Automo directory skeleton without overwriting state."""
    try:
        created = initialise_mr_project(root)
    except GovernanceError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    for path in created:
        typer.echo(f"created: {path}")
    typer.echo(f"summary: {len(created)} created; existing project files preserved")


@app.command("doctor")
def doctor_command(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Diagnose package, research-state, optional GetDone, and local tooling health."""
    checks = doctor_checks(root)
    width = max(len(check.name) for check in checks)
    for check in checks:
        typer.echo(f"{check.name:<{width}}  {check.status:<8}  {check.detail}")
    if any(check.blocking and check.status == "fail" for check in checks):
        raise typer.Exit(1)


@app.command("status")
def status_command(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")] = False,
) -> None:
    """Render a concise read-only summary of current research state."""
    if (root / ".automo" / "project.yaml").is_file():
        try:
            payload = ResearchGovernance(root).status_payload()
        except GovernanceError as exc:
            raise typer.Exit(_error(str(exc))) from exc
        if as_json:
            typer.echo(json.dumps(payload, indent=2, sort_keys=True))
            return
        typer.echo("# Automo Research Status")
        typer.echo(f"Program: {payload['program']['id']}")
        hypothesis = payload["current_hypothesis"]
        if hypothesis:
            typer.echo(f"Hypothesis: {hypothesis['id']} ({hypothesis['status']})")
            typer.echo(f"Statement: {hypothesis['statement']}")
        else:
            typer.echo("Hypothesis: none active")
        typer.echo(f"Models: {len(payload['models'])}; relations: {len(payload['relations'])}")
        return
    try:
        status = project_status(root)
    except (ContractError, OSError, ValueError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    if as_json:
        typer.echo(json.dumps(status.as_dict(), indent=2, sort_keys=True))
    else:
        typer.echo(render_status(status), nl=False)


@app.command("plan")
def plan_command(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")] = False,
) -> None:
    """Show the committed next experiment, rationale, budget, and falsification."""
    if (root / ".automo" / "project.yaml").is_file():
        try:
            payload = ResearchGovernance(root).status_payload()
        except GovernanceError as exc:
            raise typer.Exit(_error(str(exc))) from exc
        if as_json:
            typer.echo(json.dumps(payload, indent=2, sort_keys=True))
            return
        hypothesis = payload.get("current_hypothesis")
        if hypothesis:
            typer.echo(f"Hypothesis: {hypothesis['id']} ({hypothesis['status']})")
            typer.echo(f"Statement: {hypothesis['statement']}")
        else:
            typer.echo("Hypothesis: none active")
        return
    try:
        payload = plan_payload(root)
    except (ContractError, OSError, ValueError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(
        json.dumps(payload, indent=2, sort_keys=True) if as_json else render_plan(payload), nl=False
    )


@app.command("run")
def run_command(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    run_id: Annotated[
        str | None, typer.Option("--run-id", help="Optional immutable run id.")
    ] = None,
) -> None:
    """Execute exactly one legal deterministic transition for the current experiment."""
    try:
        stage, evidence_path = run_next_transition(root, run_id=run_id)
    except (ContractError, ExecutionError, OSError, ValueError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Stage: {stage}")
    typer.echo(f"Evidence: {evidence_path}")
    typer.echo("Governance boundary preserved: exactly one transition executed.")


@app.command("validate")
def validate_command(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Validate research contracts and optional GetDone project records."""
    ok, errors, warnings = validate_mr_project(root)
    for warning in warnings:
        typer.echo(f"warning: {warning}")
    for error in errors:
        typer.echo(f"error: {error}", err=True)
    if not ok:
        raise typer.Exit(1)
    typer.echo(f"validation passed: {len(warnings)} warning(s)")


@experiment_app.command("next")
@app.command("next", hidden=True)
def show_next(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")] = False,
) -> None:
    """Show the committed next experiment and its reasoning."""
    try:
        experiment = ResearchProject(root).next_experiment()
    except ContractError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    payload = {
        "id": experiment.identifier,
        "status": experiment.status,
        "title": experiment.title,
        "why_next": experiment.why_next,
        "hypothesis": experiment.hypothesis,
        "expected_effect": experiment.expected_effect,
        "falsification": experiment.falsification,
        "baseline": experiment.baseline,
        "candidate_model": experiment.candidate_model,
        "feature_set": experiment.feature_set,
    }
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(f"{experiment.identifier}: {experiment.title}")
    typer.echo(f"Status: {experiment.status}")
    typer.echo(f"Why next: {experiment.why_next}")
    typer.echo(f"Hypothesis: {experiment.hypothesis}")
    typer.echo(f"Falsified when: {'; '.join(experiment.falsification)}")


@experiment_app.command("validate")
@app.command("validate-experiment", hidden=True)
def validate_experiment(
    experiment_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    catalogue: Annotated[
        Path | None,
        typer.Option("--data-catalogue", help="Optional YAML data availability catalogue."),
    ] = None,
) -> None:
    """Validate an experiment contract and its declared prerequisites."""
    from automo.contracts import load_experiment

    try:
        experiment = load_experiment(root / "research" / "experiments" / f"{experiment_id}.yaml")
    except ContractError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    data_values = _load_data_catalogue(catalogue)
    report = validate_prerequisites(
        experiment,
        MappingDataCatalogue(data_values),
        SetCapabilityCatalogue(set()),
    )
    if report.ready:
        typer.echo(f"{experiment.identifier} prerequisites are ready.")
        return
    typer.echo(f"{experiment.identifier} is blocked by {len(report.blockers)} prerequisite(s):")
    for blocker in report.blockers:
        typer.echo(f"- {blocker.type}: {blocker.requirement_id}: {blocker.reason}")
        typer.echo(f"  User action: {blocker.user_action_required}")
    raise typer.Exit(code=2)


@experiment_app.command("prepare")
@app.command("prepare-experiment", hidden=True)
def prepare_experiment(
    experiment_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    seed: Annotated[int, typer.Option("--seed", help="Deterministic fitting seed.")] = 42,
    run_id: Annotated[
        str | None, typer.Option("--run-id", help="Optional immutable run id.")
    ] = None,
) -> None:
    """Fit and validate the candidate, then persist its freeze contract."""
    from automo.contracts import load_experiment

    try:
        experiment = load_experiment(root / "research" / "experiments" / f"{experiment_id}.yaml")
        result = prepare_local_experiment(root, experiment, seed=seed, run_id=run_id)
    except (ContractError, ExecutionError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Run: {result.run_id}")
    typer.echo(f"Freeze: {result.freeze_path}")
    typer.echo(f"Validation: {result.validation_path}")
    typer.echo(f"Fingerprint: {result.configuration_fingerprint}")


@experiment_app.command("evaluate-oos")
@app.command("evaluate-oos", hidden=True)
def evaluate_oos(
    run_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Verify a frozen run and evaluate its untouched out-of-sample partition."""
    try:
        result = evaluate_local_out_of_sample(root, run_id)
    except ExecutionError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Run: {result.run_id}")
    typer.echo(f"Manifest: {result.manifest_path}")
    typer.echo(f"Out of sample: {result.out_of_sample_path}")


@experiment_app.command("run-local")
@app.command("run-experiment", hidden=True)
def run_experiment(
    experiment_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    seed: Annotated[int, typer.Option("--seed", help="Deterministic fitting seed.")] = 42,
    run_id: Annotated[
        str | None, typer.Option("--run-id", help="Optional immutable run id.")
    ] = None,
) -> None:
    """Run the supported local baseline-versus-candidate experiment."""
    from automo.contracts import load_experiment

    try:
        experiment = load_experiment(root / "research" / "experiments" / f"{experiment_id}.yaml")
        result = run_local_experiment(root, experiment, seed=seed, run_id=run_id)
    except (ContractError, ExecutionError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Run: {result.run_id}")
    typer.echo(f"Manifest: {result.manifest_path}")
    typer.echo(f"Validation: {result.validation_path}")
    typer.echo(f"Out of sample: {result.out_of_sample_path}")
    typer.echo(f"Fingerprint: {result.configuration_fingerprint}")


@stability_app.command("run")
@app.command("run-temporal-stability", hidden=True)
def run_temporal_stability_command(
    experiment_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    run_id: Annotated[
        str | None, typer.Option("--run-id", help="Optional immutable run id.")
    ] = None,
) -> None:
    """Run only the experiment's committed predefined temporal folds."""
    from automo.contracts import load_experiment

    try:
        experiment = load_experiment(root / "research" / "experiments" / f"{experiment_id}.yaml")
        result = run_temporal_stability(root, experiment, run_id=run_id)
    except (ContractError, ExecutionError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Run: {result.run_id}")
    typer.echo(f"Temporal stability: {result.evidence_path}")
    typer.echo(f"Folds executed: {result.fold_count}")
    typer.echo(f"Fingerprint: {result.configuration_fingerprint}")


@experiment_app.command("decide")
@app.command("decide", hidden=True)
def decide(
    run_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Create one immutable decision from completed run evidence without refitting."""
    try:
        result = decide_local_run(root, run_id)
    except DecisionError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Run: {result.run_id}")
    typer.echo(f"Outcome: {result.outcome}")
    typer.echo(f"Decision: {result.decision_path}")
    for reason in result.reasons:
        typer.echo(f"Reason: {reason}")


@features_app.command("dispose")
@app.command("dispose-features", hidden=True)
def dispose_features(
    run_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Create immutable bounded feature-group dispositions from completed evidence."""
    try:
        result = dispose_local_features(root, run_id)
    except FeatureDispositionError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Run: {result.run_id}")
    typer.echo(f"Feature dispositions: {result.disposition_path}")
    for feature_group_id, outcome in result.outcomes:
        typer.echo(f"{feature_group_id}: {outcome}")


@findings_app.command("propose-next")
@app.command("propose-next", hidden=True)
def propose_next(
    run_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Derive structured findings and exactly one falsifiable next experiment."""
    try:
        result = propose_next_experiment(root, run_id)
    except FindingError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Run: {result.run_id}")
    typer.echo(f"Findings: {result.findings_path}")
    typer.echo(f"Next experiment: {result.next_experiment_id}")
    typer.echo(f"Specification: {result.next_experiment_path}")


@promotion_app.command("recommend")
@app.command("recommend-promotion", hidden=True)
def recommend_promotion_command(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    recommendation_id: Annotated[str, typer.Option("--recommendation-id")] = "promotion-0001",
) -> None:
    """Create one immutable, non-deploying champion/challenger recommendation."""
    try:
        result = recommend_promotion(root, recommendation_id=recommendation_id)
    except PromotionError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Outcome: {result.outcome}")
    typer.echo(f"Recommendation: {result.recommendation_path}")
    for reason in result.reasons:
        typer.echo(f"Reason: {reason}")


@capability_app.command("status")
@app.command("capability-status", hidden=True)
def capability_status(
    request_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    enabled: Annotated[
        bool, typer.Option("--enabled", help="Enable explicit GetDone delegation.")
    ] = False,
) -> None:
    """Inspect whether a committed capability request can be delegated."""
    workflow = GetDoneCapabilityWorkflow(enabled=enabled)
    try:
        payload = inspect_capability(root, request_id, workflow)
    except CapabilityLifecycleError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Request: {payload['request_id']}")
    typer.echo(f"Capability: {payload['capability_id']}")
    typer.echo(f"Provider: {payload['provider']}")
    typer.echo(f"Ready: {'yes' if payload['ready_for_delegation'] else 'no'}")
    typer.echo(str(payload["detail"]))


@capability_app.command("handoff")
def capability_handoff(
    request_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Create a bounded GetDone development handoff without mutating ``.agent``."""
    try:
        path = create_getdone_handoff(root, request_id)
    except CapabilityLifecycleError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Handoff: {path}")
    typer.echo("Automo did not write .agent/; run GetDone development guidance separately.")


@capability_app.command("fulfill")
@app.command("fulfill-capability", hidden=True)
def fulfill_capability_command(
    request_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    attempt_id: Annotated[
        str, typer.Option("--attempt-id", help="Immutable capability attempt id.")
    ] = "attempt-0001",
    enabled: Annotated[
        bool, typer.Option("--enabled", help="Enable explicit GetDone delegation.")
    ] = False,
) -> None:
    """Create one immutable bounded capability-attempt result."""
    workflow = GetDoneCapabilityWorkflow(enabled=enabled)
    try:
        result = fulfill_capability(root, request_id, attempt_id=attempt_id, delegate=workflow)
    except CapabilityLifecycleError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(f"Request: {result.request_id}")
    typer.echo(f"Attempt: {result.attempt_id}")
    typer.echo(f"Status: {result.status}")
    typer.echo(f"Result: {result.result_path}")
    typer.echo(f"Detail: {result.detail}")


@integration_app.command("status")
@app.command("integration-status", hidden=True)
def integration_status(
    enabled: Annotated[
        bool,
        typer.Option("--enabled", help="Report status as if GetDone delegation is enabled."),
    ] = False,
) -> None:
    """Inspect the optional GetDone integration without requiring it."""
    status = GetDoneCapabilityWorkflow(enabled=enabled).status()
    typer.echo(f"Provider: {status.provider}")
    typer.echo(f"Installed: {'yes' if status.installed else 'no'}")
    typer.echo(f"Enabled: {'yes' if status.enabled else 'no'}")
    typer.echo(f"Compatible: {'yes' if status.compatible else 'no'}")
    typer.echo(status.detail)


def _load_data_catalogue(path: Path | None) -> dict[str, DataAvailability]:
    if path is None:
        return {}
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise typer.BadParameter("data catalogue must be a mapping")
    values: dict[str, DataAvailability] = {}
    for identifier, item in raw.items():
        if not isinstance(identifier, str) or not isinstance(item, dict):
            raise typer.BadParameter("data catalogue entries must be string-keyed mappings")
        values[identifier] = DataAvailability(
            available=bool(item.get("available", False)),
            fields=frozenset(item.get("fields", [])),
            start=item.get("start"),
            end=item.get("end"),
            detail=item.get("detail"),
        )
    return values


def _error(message: str) -> int:
    typer.echo(f"Error: {message}", err=True)
    return 1


@models_app.command("pool")
def models_pool(
    pool_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    store = FilesystemPoolStore(root / ".automo" / "pools")
    history = store.history(pool_id)
    if not history:
        raise typer.Exit(_error(f"unknown or empty model pool: {pool_id}"))
    snapshot = history[-1]
    typer.echo(f"Pool: {snapshot.pool_id}")
    typer.echo(f"Iteration: {snapshot.iteration_id}")
    typer.echo(f"Active: {', '.join(snapshot.active_model_ids) or '-'}")
    typer.echo(f"Selected: {', '.join(snapshot.selected_model_ids) or '-'}")


@models_app.command("pool-history")
def models_pool_history(
    pool_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    store = FilesystemPoolStore(root / ".automo" / "pools")
    for snapshot in store.history(pool_id):
        typer.echo(
            f"{snapshot.iteration_id}  active={','.join(snapshot.active_model_ids)}  selected={','.join(snapshot.selected_model_ids)}"
        )


def main() -> None:
    app()


if __name__ == "__main__":
    main()


def _model_registry(root: Path) -> FilesystemModelRegistry:
    from automo.runtime.builtins import LinearModelJsonCodec

    return FilesystemModelRegistry(root / ".automo" / "registry", codecs=(LinearModelJsonCodec(),))


def _primary_benchmark(record):
    if not record.latest_benchmarks:
        return None
    return tuple(record.latest_benchmarks.values())[-1]


@models_app.command("list")
def models_list(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    status: Annotated[
        str | None, typer.Option("--status", help="Optional lifecycle status filter.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")] = False,
) -> None:
    """List registered models without loading model artifacts."""
    try:
        parsed = ModelStatus(status) if status else None
        records = _model_registry(root).list_models(status=parsed)
    except (RegistryError, ValueError) as exc:
        raise typer.Exit(_error(str(exc))) from exc
    payload = []
    for record in records:
        benchmark = _primary_benchmark(record)
        payload.append(
            {
                "id": record.manifest.id,
                "implementation": record.manifest.implementation,
                "objective": record.manifest.objective_id,
                "status": record.status.value,
                "metric": benchmark.metric_id if benchmark else None,
                "value": benchmark.value if benchmark else None,
                "calibration": record.latest_calibration.id if record.latest_calibration else None,
            }
        )
    if as_json:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    if not payload:
        typer.echo("No registered models.")
        return
    typer.echo(
        "ID             IMPLEMENTATION          STATUS      OBJECTIVE          METRIC        VALUE"
    )
    for item in payload:
        value = "-" if item["value"] is None else f"{item['value']:.6g}"
        typer.echo(
            f"{item['id']:<14} {item['implementation']:<23} {item['status']:<11} {item['objective']:<18} {(item['metric'] or '-'):<13} {value}"
        )


@models_app.command("active")
def models_active(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    models_list(root=root, status=ModelStatus.ACTIVE.value, as_json=False)


@models_app.command("archived")
def models_archived(
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    models_list(root=root, status=ModelStatus.ARCHIVED.value, as_json=False)


@models_app.command("show")
def models_show(
    model_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")] = False,
) -> None:
    """Show reconstructable identity, lineage, calibration and latest benchmark evidence."""
    try:
        record = _model_registry(root).get_record(model_id)
    except RegistryError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    payload = {
        "manifest": record.manifest.as_dict(),
        "provenance": record.provenance.as_dict(),
        "status": record.status.value,
        "latest_calibration": record.latest_calibration.as_dict()
        if record.latest_calibration
        else None,
        "latest_benchmarks": {
            key: value.as_dict() for key, value in record.latest_benchmarks.items()
        },
    }
    if as_json:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    typer.echo(f"Model: {record.manifest.id}")
    typer.echo(f"Status: {record.status.value}")
    typer.echo(f"Implementation: {record.manifest.implementation}")
    typer.echo(f"Model spec: {record.manifest.model_spec_id}")
    typer.echo(f"Objective: {record.manifest.objective_id}")
    typer.echo(f"Feature set: {record.manifest.feature_set_id}")
    typer.echo(f"Data snapshot: {record.provenance.data_snapshot_id}")
    typer.echo(f"Artifact hash: {record.manifest.artifact_hash}")
    typer.echo(f"Calibration: {record.latest_calibration.id if record.latest_calibration else '-'}")
    if record.latest_benchmarks:
        typer.echo("Latest benchmarks:")
        for item in record.latest_benchmarks.values():
            typer.echo(f"- {item.metric_id} [{item.scope}/{item.split}]: {item.value}")


def _comparison_payload(left, right):
    if left.manifest.objective_id != right.manifest.objective_id:
        raise RegistryError(
            "models have different objectives and are not directly comparable: "
            f"{left.manifest.objective_id} != {right.manifest.objective_id}"
        )
    return {
        "objective": left.manifest.objective_id,
        "models": {
            left.manifest.id: {
                "implementation": left.manifest.implementation,
                "feature_set": left.manifest.feature_set_id,
                "data_snapshot": left.provenance.data_snapshot_id,
                "status": left.status.value,
                "calibration": left.latest_calibration.id if left.latest_calibration else None,
                "benchmarks": {key: value.value for key, value in left.latest_benchmarks.items()},
            },
            right.manifest.id: {
                "implementation": right.manifest.implementation,
                "feature_set": right.manifest.feature_set_id,
                "data_snapshot": right.provenance.data_snapshot_id,
                "status": right.status.value,
                "calibration": right.latest_calibration.id if right.latest_calibration else None,
                "benchmarks": {key: value.value for key, value in right.latest_benchmarks.items()},
            },
        },
    }


@models_app.command("compare")
def models_compare(
    left_id: str,
    right_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Compare two models only when their objectives are compatible."""
    try:
        registry = _model_registry(root)
        payload = _comparison_payload(registry.get_record(left_id), registry.get_record(right_id))
    except RegistryError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@models_app.command("diff")
def models_diff(
    left_id: str,
    right_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Show only identity/provenance fields that differ between two comparable models."""
    try:
        registry = _model_registry(root)
        left = registry.get_record(left_id)
        right = registry.get_record(right_id)
        _comparison_payload(left, right)
    except RegistryError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    left_values = {
        "implementation": left.manifest.implementation,
        "model_spec": left.manifest.model_spec_id,
        "feature_set": left.manifest.feature_set_id,
        "data_snapshot": left.provenance.data_snapshot_id,
        "data_snapshot_hash": left.provenance.data_snapshot_hash,
        "runner": left.provenance.runner_implementation,
        "code_revision": left.provenance.code_revision,
        "calibration": left.latest_calibration.id if left.latest_calibration else None,
    }
    right_values = {
        "implementation": right.manifest.implementation,
        "model_spec": right.manifest.model_spec_id,
        "feature_set": right.manifest.feature_set_id,
        "data_snapshot": right.provenance.data_snapshot_id,
        "data_snapshot_hash": right.provenance.data_snapshot_hash,
        "runner": right.provenance.runner_implementation,
        "code_revision": right.provenance.code_revision,
        "calibration": right.latest_calibration.id if right.latest_calibration else None,
    }
    differences = {
        key: {left_id: left_values[key], right_id: right_values[key]}
        for key in left_values
        if left_values[key] != right_values[key]
    }
    typer.echo(json.dumps(differences, indent=2, sort_keys=True))


@models_app.command("history")
def models_history(
    model_id: str,
    root: Annotated[Path, typer.Option("--root", help="Automo project root.")] = _root_option(),
) -> None:
    """Show append-only model lifecycle history."""
    try:
        registry = _model_registry(root)
        registry.get_manifest(model_id)
        events = registry.history(model_id)
    except RegistryError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    for event in events:
        previous = event.from_status.value if event.from_status else "-"
        typer.echo(f"{event.at}  {previous} -> {event.to_status.value}  {event.reason}")
