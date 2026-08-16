from pathlib import Path

import pytest

from automo.runtime import PluginLoadError, load_project_plugin


def test_project_plugin_can_be_loaded_from_thin_factory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "demo_plugin.py"
    package.write_text(
        "from automo.runtime import ResearchPlugin\n"
        "def create_plugin():\n"
        "    return ResearchPlugin(id='demo', data_sources=(), feature_computers=(), "
        "feature_sets=(), objectives=(), metrics=(), model_specs=(), model_runners=())\n",
        encoding="utf-8",
    )
    (tmp_path / "automo.toml").write_text(
        '[project]\nplugin = "demo_plugin:create_plugin"\n', encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    plugin = load_project_plugin(tmp_path)
    assert plugin.id == "demo"


def test_missing_project_plugin_is_actionable(tmp_path: Path) -> None:
    with pytest.raises(PluginLoadError, match=r"automo\.toml"):
        load_project_plugin(tmp_path)
