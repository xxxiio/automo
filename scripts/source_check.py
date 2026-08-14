from __future__ import annotations

import ast
from pathlib import Path
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

    forbidden_paths = (
        ROOT / "src/getdone_mr",
        ROOT / "build",
        ROOT / "runs",
        ROOT / "recommendations",
        ROOT / "capability-results",
    )
    for path in forbidden_paths:
        if path.exists():
            errors.append(f"release source tree contains generated/legacy path: {path.relative_to(ROOT)}")
    for path in ROOT.glob("src/*.egg-info"):
        errors.append(f"release source tree contains generated packaging metadata: {path.relative_to(ROOT)}")
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('source-check: passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
