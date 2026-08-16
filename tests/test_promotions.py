import json
import shutil
from pathlib import Path

import pytest

from automo.promotions import PromotionError, PromotionOutcome, recommend_promotion

ROOT = Path(__file__).parents[1]
FIXTURE_RUNS = ROOT / "tests/fixtures/runs"


def copy_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(
            ".pytest_cache", "__pycache__", "recommendations", "build", "dist", "*.egg-info"
        ),
    )
    shutil.copytree(FIXTURE_RUNS, root / "runs")
    return root


def test_promotes_when_every_gate_passes(tmp_path: Path) -> None:
    root = copy_project(tmp_path)
    result = recommend_promotion(root)
    payload = json.loads(result.recommendation_path.read_text())
    assert result.outcome is PromotionOutcome.PROMOTE_CHALLENGER
    assert payload["deployment_performed"] is False
    assert payload["refit_performed"] is False
    assert len(payload["evidence"]) == 4


def test_retains_champion_when_operational_gate_fails(tmp_path: Path) -> None:
    root = copy_project(tmp_path)
    policy = root / "research/policies/POLICY-PROMOTION-0001.yaml"
    policy.write_text(
        policy.read_text().replace("maximum_duration_ms: 50.0", "maximum_duration_ms: 0.0")
    )
    result = recommend_promotion(root)
    assert result.outcome is PromotionOutcome.RETAIN_CHAMPION


def test_missing_evidence_prevents_recommendation(tmp_path: Path) -> None:
    root = copy_project(tmp_path)
    (root / "runs/experiment-0006-temporal/temporal-stability.json").unlink()
    with pytest.raises(PromotionError):
        recommend_promotion(root)


def test_recommendation_is_immutable(tmp_path: Path) -> None:
    root = copy_project(tmp_path)
    recommend_promotion(root)
    with pytest.raises(PromotionError):
        recommend_promotion(root)
