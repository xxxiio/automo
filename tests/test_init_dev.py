from __future__ import annotations

from pathlib import Path

from automo.dev import bootstrap as bootstrap_module


def test_bootstrap_installs_poetry_dev_environment_then_hook(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    monkeypatch.setattr(
        bootstrap_module.shutil,
        "which",
        lambda name: "/usr/bin/poetry" if name == "poetry" else None,
    )
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, root: Path) -> None:
        commands.append(command)

    monkeypatch.setattr(bootstrap_module, "_run", fake_run)

    assert bootstrap_module.bootstrap(root) == 0
    assert commands == [
        ["/usr/bin/poetry", "install", "--with", "dev"],
        ["/usr/bin/poetry", "run", "pre-commit", "install", "--install-hooks"],
    ]


def test_bootstrap_rejects_non_git_directory(tmp_path: Path) -> None:
    assert bootstrap_module.bootstrap(tmp_path) == 2


def test_bootstrap_requires_poetry(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    monkeypatch.setattr(bootstrap_module.shutil, "which", lambda name: None)
    assert bootstrap_module.bootstrap(root) == 2
