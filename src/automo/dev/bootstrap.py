"""Bootstrap an Automo contributor checkout using Poetry and pre-commit."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _run(command: list[str], *, root: Path) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=root, check=True)


def bootstrap(root: Path) -> int:
    """Install developer dependencies and the repository pre-commit hook."""
    root = root.resolve()
    if not (root / ".git").exists():
        print("error: developer bootstrap must run from a Git checkout", file=sys.stderr)
        return 2

    poetry = shutil.which("poetry")
    if poetry is None:
        print(
            "error: Poetry is required for Automo development; install Poetry first",
            file=sys.stderr,
        )
        return 2

    _run([poetry, "install", "--with", "dev"], root=root)
    _run([poetry, "run", "pre-commit", "install", "--install-hooks"], root=root)
    print(
        "developer bootstrap complete: Poetry environment ready and Git pre-commit hook installed"
    )
    return 0
