from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_source_check_passes() -> None:
    completed = subprocess.run(
        [sys.executable, 'scripts/source_check.py'], cwd=ROOT, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr


def test_command_reference_has_no_placeholders() -> None:
    text = (ROOT / '.agent' / 'command-reference.md').read_text(encoding='utf-8')
    assert '<!--' not in text
    assert 'Canonical full health gate' in text
    assert 'scripts/health_gate.py' in text


def test_distribution_has_no_required_getdone_dependency() -> None:
    text = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    base = text.split('[project.optional-dependencies]', 1)[0]
    assert 'get-done' not in base
    assert 'getdone = ["getdone-dev' in text
