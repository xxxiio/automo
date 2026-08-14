from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print(f"\n== {label} ==")
    print("$", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True, env=env)


def _smoke_install(artifact: Path, *, label: str) -> None:
    with tempfile.TemporaryDirectory(prefix=f"automo-{label}-") as tmp:
        root = Path(tmp)
        target = root / "site"
        target.mkdir()
        run(
            f"{label} install",
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--no-build-isolation",
                "--target",
                str(target),
                str(artifact),
            ],
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = str(target)

        def smoke(name: str, args: list[str], *, cwd: Path = root) -> None:
            run(name, [sys.executable, "-m", "automo.cli", *args], cwd=cwd, env=env)

        smoke(f"{label} CLI help", ["--help"])
        smoke(f"{label} standalone integration", ["integration", "status"])

        project = root / "project"
        smoke(f"{label} init", ["init", "--root", str(project)])
        smoke(f"{label} validate fresh project", ["validate", "--root", str(project)])
        smoke(f"{label} doctor fresh project", ["doctor", "--root", str(project)])



def _strip_sdist_egg_info(path: Path) -> None:
    """Remove setuptools-generated egg-info from the distributable source archive."""
    with tempfile.TemporaryDirectory(prefix="automo-sdist-clean-") as tmp:
        root = Path(tmp)
        with tarfile.open(path, "r:gz") as archive:
            archive.extractall(root, filter="data")
        for egg_info in root.rglob("*.egg-info"):
            if egg_info.is_dir():
                shutil.rmtree(egg_info)
        cleaned = path.with_suffix(path.suffix + ".clean")
        top = next(root.iterdir())
        with tarfile.open(cleaned, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            archive.add(top, arcname=top.name)
        os.replace(cleaned, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical Automo offline release health gate.")
    parser.add_argument("--keep-dist", action="store_true", help="Keep built artifacts in dist/.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest when it already ran in CI.")
    args = parser.parse_args()
    dist = ROOT / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir()

    run("source hygiene", [sys.executable, "scripts/source_check.py"])
    run("compile", [sys.executable, "-m", "compileall", "-q", "src", "tests", "scripts", "examples"])
    if not args.skip_tests:
        run("tests", [sys.executable, "-m", "pytest", "-q"])

    examples_env = dict(os.environ)
    examples_env["PYTHONPATH"] = str(ROOT / "src")
    for example in sorted((ROOT / "examples").glob("*/example.py")):
        run(f"example {example.parent.name}", [sys.executable, str(example)], env=examples_env)

    run(
        "wheel build",
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "-w", str(dist)],
    )
    # Build the sdist directly through the configured setuptools PEP 517 backend, avoiding a
    # dependency on the optional `build` frontend in offline development environments.
    run(
        "sdist build",
        [
            sys.executable,
            "-c",
            f"import setuptools.build_meta as b; print(b.build_sdist({str(dist)!r}))",
        ],
    )

    wheels = sorted(dist.glob("automo-*.whl"))
    sdists = sorted(dist.glob("automo-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError(f"expected one wheel and one sdist, found {len(wheels)} / {len(sdists)}")
    wheel, sdist = wheels[0], sdists[0]
    _strip_sdist_egg_info(sdist)
    shutil.rmtree(ROOT / "src" / "automo.egg-info", ignore_errors=True)

    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if not any(name.endswith("automo/cli.py") for name in names):
            raise RuntimeError("wheel does not contain automo/cli.py")
        if any("getdone_mr" in name or "getdone-mr" in name for name in names):
            raise RuntimeError("wheel unexpectedly contains the legacy GetDone MR package identity")

    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()
        forbidden = ("/runs/", "/recommendations/", "/build/", ".egg-info/")
        bad = [name for name in names if any(token in f"/{name}/" for token in forbidden)]
        if bad:
            raise RuntimeError(f"sdist contains generated/runtime artifacts: {bad[:5]}")
        if any("getdone_mr" in name or "getdone-mr" in name for name in names):
            raise RuntimeError("sdist unexpectedly contains the legacy GetDone MR package identity")

    _smoke_install(wheel, label="wheel")
    _smoke_install(sdist, label="sdist")

    if not args.keep_dist:
        shutil.rmtree(dist)
    print("\nhealth-gate: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
