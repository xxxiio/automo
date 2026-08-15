#!/usr/bin/env python
"""Bootstrap an Automo contributor checkout using only the Python standard library.

This intentionally mirrors PPW's post-generation developer setup: bootstrap the
external tools with the currently selected Python, install the standard Git
pre-commit hook, then let Poetry install/manage the project environment.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_LEGACY_AUTOMO_HOOKS_PATH = ".githooks"


def _run(command: list[str], *, root: Path) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=root, check=True)


def _capture(command: list[str], *, root: Path) -> str:
    result = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _installed_hook_path(root: Path) -> Path:
    value = _capture(["git", "rev-parse", "--git-path", "hooks/pre-commit"], root=root)
    path = Path(value)
    return path if path.is_absolute() else root / path


def bootstrap(root: Path = ROOT) -> int:
    """Install pre-commit, Poetry, dev dependencies, and the standard Git hook."""
    root = root.resolve()
    if not (root / ".git").exists():
        print("error: developer bootstrap must run from a Git checkout", file=sys.stderr)
        return 2

    hooks_path = _capture(["git", "config", "--local", "--get", "core.hooksPath"], root=root)
    if hooks_path == _LEGACY_AUTOMO_HOOKS_PATH:
        _run(["git", "config", "--local", "--unset-all", "core.hooksPath"], root=root)

    # PPW bootstrap order: current Python installs pre-commit, then the standard
    # Git hook; current Python installs Poetry; Poetry installs project deps.
    _run([sys.executable, "-m", "pip", "install", "pre-commit"], root=root)
    _run([sys.executable, "-m", "pre_commit", "install"], root=root)

    _run([sys.executable, "-m", "pip", "install", "poetry"], root=root)
    _run([sys.executable, "-m", "poetry", "install", "--with", "dev"], root=root)

    hook_path = _installed_hook_path(root)
    if not hook_path.is_file() or not os.access(hook_path, os.X_OK):
        print(
            f"error: pre-commit hook was not installed as an executable: {hook_path}",
            file=sys.stderr,
        )
        return 2

    print(f"developer bootstrap complete: executable pre-commit hook installed at {hook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(bootstrap())
