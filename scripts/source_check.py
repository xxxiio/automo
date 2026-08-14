from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECK_DIRS = (ROOT / 'src', ROOT / 'tests', ROOT / 'scripts')


def main() -> int:
    errors: list[str] = []
    for base in CHECK_DIRS:
        for path in sorted(base.rglob('*.py')):
            text = path.read_text(encoding='utf-8')
            try:
                ast.parse(text, filename=str(path))
            except SyntaxError as exc:
                errors.append(f'{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}')
            for lineno, line in enumerate(text.splitlines(), start=1):
                if line.rstrip() != line:
                    errors.append(f'{path.relative_to(ROOT)}:{lineno}: trailing whitespace')
                if '\t' in line:
                    errors.append(f'{path.relative_to(ROOT)}:{lineno}: tab character')

    forbidden_prefixes = (
        "src/getdone_mr/",
        "build/",
        "runs/",
        "recommendations/",
        "capability-results/",
    )
    forbidden_suffixes = (".egg-info/",)

    tracked: list[str] | None = None
    if (ROOT / ".git").exists():
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0:
            tracked = [item.decode() for item in completed.stdout.split(b"\0") if item]

    if tracked is not None:
        for rel in tracked:
            if any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in forbidden_prefixes):
                errors.append(f"release source tracks generated/legacy path: {rel}")
            if any(part.endswith(suffix.rstrip("/")) for part in Path(rel).parts for suffix in forbidden_suffixes):
                errors.append(f"release source tracks generated packaging metadata: {rel}")
    else:
        # Source archives do not contain .git metadata. In that case validate the
        # extracted source boundary before tooling creates ignored build metadata.
        for prefix in forbidden_prefixes:
            path = ROOT / prefix.rstrip("/")
            if path.exists():
                errors.append(f"release source tree contains generated/legacy path: {path.relative_to(ROOT)}")
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('source-check: passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
