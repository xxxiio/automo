from __future__ import annotations

from pathlib import Path

import scripts.init_dev as init_dev


def test_init_dev_syncs_environment_then_installs_hook(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    monkeypatch.setattr(init_dev, "ROOT", root)
    monkeypatch.setattr(
        init_dev.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None
    )

    commands: list[list[str]] = []

    def fake_run(command: list[str]) -> None:
        commands.append(command)
        if command[:2] == ["/usr/bin/uv", "sync"]:
            pre_commit = init_dev._pre_commit_path()
            pre_commit.parent.mkdir(parents=True, exist_ok=True)
            pre_commit.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(init_dev, "_run", fake_run)

    assert init_dev.main() == 0
    assert commands[0] == ["/usr/bin/uv", "sync", "--extra", "dev"]
    assert commands[1] == [str(init_dev._pre_commit_path()), "install", "--install-hooks"]


def test_init_dev_rejects_non_git_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(init_dev, "ROOT", tmp_path)
    monkeypatch.setattr(init_dev.shutil, "which", lambda name: "/usr/bin/uv")
    assert init_dev.main() == 2
