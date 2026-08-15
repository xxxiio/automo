# Publishing Automo

Automo uses GitHub Actions for continuous integration, PyPI publishing, and documentation deployment.

## Continuous integration

`.github/workflows/ci.yml` runs on pushes to `main` and on pull requests. Its quality job runs the canonical full-repository pre-commit gate, while a separate Python 3.11/3.12/3.13 matrix runs `poetry run pytest -q` under each supported interpreter. Packaging/smoke checks and strict documentation builds remain separate jobs. Successful `main` CI also deploys that exact documentation build to GitHub Pages.

## PyPI releases

Package publication is intentionally separate from ordinary CI. `.github/workflows/publish-pypi.yml` runs only when a `v*` tag is pushed. It:

1. checks out the tagged commit and verifies the tag points to the current `main` HEAD;
2. requires a successful `ci.yml` push run for that exact `main` commit instead of rerunning the quality/test/docs matrix;
3. verifies that a tag such as `v0.3.0a1` matches the package version `0.3.0a1`;
4. builds both the wheel and source distribution;
5. validates the distributions; and
6. publishes the exact built artifacts to PyPI using Trusted Publishing (OIDC).

No long-lived PyPI API token is required or expected.

### One-time PyPI setup

Create the `automo` project on PyPI, or configure a pending Trusted Publisher for the first upload, with these values:

- GitHub owner: `xlatomapp`
- Repository: `automo`
- Workflow filename: `publish-pypi.yml`
- Environment: `pypi`

In the GitHub repository, create an environment named `pypi`. A required reviewer is recommended so that publication remains an explicit approval boundary after the tag is pushed.

### Release procedure

1. Merge the release candidate into `main` and make sure CI is green.
2. Tag the exact release commit, for example `v0.3.0a1`.
3. Push only that tag, for example `git push origin v0.3.0a1`.
4. Approve the `pypi` environment deployment if environment protection requires it.
5. Confirm that the `publish-pypi` workflow published both distributions.

Do not reuse an already-published version: PyPI distributions are immutable by filename/version.

## GitHub Pages documentation

Documentation validation and deployment are part of `.github/workflows/ci.yml`: every PR/main run performs a strict Zensical build, while only a successful push to `main` uploads and deploys the generated `site/` directory through GitHub Pages. This prevents the docs from being built twice by separate workflows.

One-time repository setup:

1. Open **Settings → Pages**.
2. Set **Build and deployment → Source** to **GitHub Actions**.
3. Merge or push the workflow to `main`.

The configured project URL is:

`https://xlatomapp.github.io/automo/`


## Release safety model

PyPI publication uses a dedicated tag-only workflow and only the publishing job receives `id-token: write`. The `pypi` GitHub environment is the intended location for deployment protection. GitHub Pages deployment happens only after the shared CI quality, package-health, and docs jobs pass; only the deployment job receives `pages: write` plus `id-token: write`.
