import re
import tomllib
from pathlib import Path


def test_pypi_project_urls_include_repository_and_documentation() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["urls"]["Repository"] == "https://github.com/xxxiio/automo"
    assert project["urls"]["Documentation"] == "https://xxxiio.github.io/automo/"
    assert project["urls"]["Issues"] == "https://github.com/xxxiio/automo/issues"


def test_readme_markdown_links_are_safe_when_rendered_on_pypi() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)
    relative = [
        target for target in targets if "://" not in target and not target.startswith("mailto:")
    ]
    assert relative == []


def test_docs_and_example_readme_relative_links_resolve() -> None:
    documents = [*Path("docs").rglob("*.md"), *Path("examples").rglob("README.md")]
    broken: list[tuple[str, str]] = []
    for document in documents:
        text = document.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            path = target.split("#", 1)[0]
            if not path or "://" in path or path.startswith("mailto:"):
                continue
            if not (document.parent / path).resolve().exists():
                broken.append((str(document), target))
    assert broken == []
