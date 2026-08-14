"""Runtime access to the package version.

The canonical version is declared once in ``pyproject.toml``. Installed builds read the
standard distribution metadata; source checkouts fall back to the project metadata so the
CLI remains usable before installation.
"""

from __future__ import annotations

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _source_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        raw = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        value = raw["project"]["version"]
    except (FileNotFoundError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError("Automo package version is unavailable") from exc
    if not isinstance(value, str) or not value:
        raise RuntimeError("Automo project.version must be a non-empty string")
    return value


def package_version() -> str:
    try:
        return version("automo")
    except PackageNotFoundError:
        return _source_version()


__version__ = package_version()
