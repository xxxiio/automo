from __future__ import annotations

from pathlib import Path

import yaml

from automo.guidance import select_guidance, validate_guidance_pack

ROOT = Path(__file__).resolve().parent


def main() -> None:
    errors = validate_guidance_pack()
    if errors:
        raise SystemExit("guidance validation failed: " + "; ".join(errors))
    data = yaml.safe_load((ROOT / "walkthrough.yaml").read_text(encoding="utf-8"))
    task_sequence = (
        "hypothesis-planning",
        "experiment-design",
        "model-diagnosis",
        "hypothesis-conclusion",
    )
    for task in task_sequence:
        print(f"{task}: {len(select_guidance(task))} guidance documents")
    for hypothesis in data["hypotheses"]:
        print(
            f"{hypothesis['id']}: {hypothesis['conclusion']} -> {hypothesis['project_implication']}"
        )


if __name__ == "__main__":
    main()
