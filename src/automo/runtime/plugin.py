from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import importlib.util
import sys
import tomllib
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from .contracts import ResearchPlugin


class PluginLoadError(RuntimeError):
    """Raised when an Automo project plugin cannot be resolved safely."""


def load_project_plugin(root: Path) -> ResearchPlugin:
    """Load the project plugin declared in ``automo.toml``.

    Supported declarations:

    ``plugin = "package.module:create_plugin"``

    or an installed entry point name from ``automo.plugins``:

    ``plugin = "entrypoint:my-project"``
    """
    config_path = root / "automo.toml"
    if not config_path.is_file():
        raise PluginLoadError(f"Automo project config is missing: {config_path}")
    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    project = raw.get("project")
    if not isinstance(project, dict):
        raise PluginLoadError("automo.toml must contain a [project] table")
    declaration = project.get("plugin")
    if not isinstance(declaration, str) or not declaration.strip():
        raise PluginLoadError("[project].plugin must be a non-empty string")
    declaration = declaration.strip()
    if declaration.startswith("entrypoint:"):
        return _load_entrypoint(declaration.removeprefix("entrypoint:"))
    return _load_import_path(declaration, root)


def _load_import_path(declaration: str, root: Path) -> ResearchPlugin:
    module_name, separator, attribute = declaration.partition(":")
    if not separator or not module_name or not attribute:
        raise PluginLoadError("plugin import must use 'package.module:factory' syntax")
    local_module = root.resolve() / (module_name.replace(".", "/") + ".py")
    try:
        if local_module.is_file():
            digest = hashlib.sha256(str(local_module).encode()).hexdigest()[:12]
            local_name = f"_automo_project_{digest}"
            spec = importlib.util.spec_from_file_location(local_name, local_module)
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot create import spec for {local_module}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            root_text = str(root.resolve())
            inserted = root_text not in sys.path
            if inserted:
                sys.path.insert(0, root_text)
            try:
                module = importlib.import_module(module_name)
            finally:
                if inserted:
                    with suppress(ValueError):
                        sys.path.remove(root_text)
        factory = getattr(module, attribute)
    except (ImportError, AttributeError) as exc:
        raise PluginLoadError(f"cannot load project plugin {declaration!r}: {exc}") from exc
    return _coerce_plugin(factory, declaration)


def _load_entrypoint(name: str) -> ResearchPlugin:
    matches = [
        entry
        for entry in importlib.metadata.entry_points(group="automo.plugins")
        if entry.name == name
    ]
    if len(matches) != 1:
        raise PluginLoadError(
            f"expected exactly one automo.plugins entry point named {name!r}; found {len(matches)}"
        )
    try:
        factory = matches[0].load()
    except (
        Exception
    ) as exc:  # pragma: no cover - delegated import failures are environment-specific
        raise PluginLoadError(f"cannot load entry point {name!r}: {exc}") from exc
    return _coerce_plugin(factory, f"entrypoint:{name}")


def _coerce_plugin(value: object, source: str) -> ResearchPlugin:
    plugin = value() if isinstance(value, Callable) else value
    if not isinstance(plugin, ResearchPlugin):
        raise PluginLoadError(f"{source!r} did not resolve to a ResearchPlugin")
    return plugin
