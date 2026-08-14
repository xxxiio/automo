from pathlib import Path
import os
import subprocess
import sys


def test_onboarding_examples_run() -> None:
    root = Path(__file__).resolve().parents[1]
    examples = [
        "basic-supervised/example.py",
        "custom-trainer/example.py",
        "meta-model/example.py",
        "structured-output/example.py",
        "id-only-data/example.py",
        "end-to-end/example.py",
        "research-guidance/example.py",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    for relative in examples:
        completed = subprocess.run(
            [sys.executable, str(root / "examples" / relative)],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
        )
        assert completed.returncode == 0, f"{relative}: {completed.stderr}\n{completed.stdout}"
