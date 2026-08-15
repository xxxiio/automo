from __future__ import annotations

import ast
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def test_init_dev_script_is_stdlib_only_and_does_not_import_automo() -> None:
    path = ROOT / "scripts" / "init_dev.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])

    assert "automo" not in imported
    assert "yaml" not in imported
    assert imported <= {
        "__future__",
        "os",
        "pathlib",
        "subprocess",
        "sys",
    }


def test_bootstrap_follows_ppw_tool_install_order(tmp_path: Path, monkeypatch) -> None:
    bootstrap_module = _load_script("automo_init_dev_test", ROOT / "scripts" / "init_dev.py")
    root = tmp_path / "repo"
    (root / ".git" / "hooks").mkdir(parents=True)
    hook = root / ".git" / "hooks" / "pre-commit"
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, root: Path) -> None:
        commands.append(command)
        if command == [sys.executable, "-m", "pre_commit", "install"]:
            _make_executable(hook)

    def fake_capture(command: list[str], *, root: Path) -> str:
        if command[:4] == ["git", "config", "--local", "--get"]:
            return ""
        if command == ["git", "rev-parse", "--git-path", "hooks/pre-commit"]:
            return ".git/hooks/pre-commit"
        return ""

    monkeypatch.setattr(bootstrap_module, "_run", fake_run)
    monkeypatch.setattr(bootstrap_module, "_capture", fake_capture)

    assert bootstrap_module.bootstrap(root) == 0
    assert commands == [
        [sys.executable, "-m", "pip", "install", "pre-commit"],
        [sys.executable, "-m", "pre_commit", "install"],
        [sys.executable, "-m", "pip", "install", "poetry"],
        [sys.executable, "-m", "poetry", "install", "--with", "dev"],
    ]
    assert hook.is_file()
    assert os.access(hook, os.X_OK)


def test_bootstrap_migrates_only_legacy_automo_core_hooks_path(tmp_path: Path, monkeypatch) -> None:
    bootstrap_module = _load_script(
        "automo_init_dev_migration_test", ROOT / "scripts" / "init_dev.py"
    )
    root = tmp_path / "repo"
    (root / ".git" / "hooks").mkdir(parents=True)
    hook = root / ".git" / "hooks" / "pre-commit"
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, root: Path) -> None:
        commands.append(command)
        if command == [sys.executable, "-m", "pre_commit", "install"]:
            _make_executable(hook)

    def fake_capture(command: list[str], *, root: Path) -> str:
        if command[:4] == ["git", "config", "--local", "--get"]:
            return ".githooks"
        if command == ["git", "rev-parse", "--git-path", "hooks/pre-commit"]:
            return ".git/hooks/pre-commit"
        return ""

    monkeypatch.setattr(bootstrap_module, "_run", fake_run)
    monkeypatch.setattr(bootstrap_module, "_capture", fake_capture)

    assert bootstrap_module.bootstrap(root) == 0
    assert ["git", "config", "--local", "--unset-all", "core.hooksPath"] in commands


def test_bootstrap_rejects_non_git_directory(tmp_path: Path) -> None:
    bootstrap_module = _load_script(
        "automo_init_dev_non_git_test", ROOT / "scripts" / "init_dev.py"
    )
    assert bootstrap_module.bootstrap(tmp_path) == 2
