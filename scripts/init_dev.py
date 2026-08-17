#!/usr/bin/env python
"""Bootstrap an Automo contributor checkout with uv using only the standard library."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_LEGACY_AUTOMO_HOOKS_PATH = ".githooks"


def _run(command: list[str], *, root: Path) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=root, check=True)


def _capture(command: list[str], *, root: Path) -> str:
    result = subprocess.run(command, cwd=root, check=False, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def _installed_hook_path(root: Path) -> Path:
    value = _capture(["git", "rev-parse", "--git-path", "hooks/pre-commit"], root=root)
    path = Path(value)
    return path if path.is_absolute() else root / path


def bootstrap(root: Path = ROOT) -> int:
    """Ensure uv is available, sync the environment, and install the Git hook."""
    root = root.resolve()
    if not (root / ".git").exists():
        print("error: developer bootstrap must run from a Git checkout", file=sys.stderr)
        return 2

    uv = shutil.which("uv")
    if uv is None:
        _run([sys.executable, "-m", "pip", "install", "uv"], root=root)
        uv_command = [sys.executable, "-m", "uv"]
    else:
        uv_command = [uv]

    hooks_path = _capture(["git", "config", "--local", "--get", "core.hooksPath"], root=root)
    if hooks_path == _LEGACY_AUTOMO_HOOKS_PATH:
        _run(["git", "config", "--local", "--unset-all", "core.hooksPath"], root=root)

    _run([*uv_command, "sync"], root=root)
    _run([*uv_command, "run", "pre-commit", "install"], root=root)

    hook_path = _installed_hook_path(root)
    if not hook_path.is_file() or not os.access(hook_path, os.X_OK):
        print(
            f"error: pre-commit hook was not installed as an executable: {hook_path}",
            file=sys.stderr,
        )
        return 2

    print(
        f"developer bootstrap complete: uv environment synced; pre-commit hook installed at {hook_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(bootstrap())
