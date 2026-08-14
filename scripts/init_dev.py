"""Bootstrap an Automo contributor checkout.

This is the PPW-style first-time developer setup: synchronise the development environment,
then install and pre-provision the repository's Git pre-commit hook. It intentionally does
not run during normal package installation.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def _pre_commit_path() -> Path:
    if os.name == "nt":
        return ROOT / ".venv" / "Scripts" / "pre-commit.exe"
    return ROOT / ".venv" / "bin" / "pre-commit"


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print("error: uv is required for Automo development; install uv first", file=sys.stderr)
        return 2
    if not (ROOT / ".git").exists():
        print("error: developer bootstrap must run from a Git checkout", file=sys.stderr)
        return 2

    _run([uv, "sync", "--extra", "dev"])
    pre_commit = _pre_commit_path()
    if not pre_commit.exists():
        print(f"error: expected pre-commit at {pre_commit} after uv sync", file=sys.stderr)
        return 2
    _run([str(pre_commit), "install", "--install-hooks"])
    print("developer bootstrap complete: Git pre-commit hook installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
