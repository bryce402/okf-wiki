# PyPI Release Guide

This package is published as **`okf-wiki`** on PyPI, separate from the upstream
`obsidian-wiki` package on PyPI. This fork uses OKF v0.2 native frontmatter.

## Prerequisites

1. **PyPI account** with Two-Factor Authentication enabled
2. **API token** scoped to the project (or `__token__` for global upload)
3. `twine` and `build` installed:

   ```bash
   pip install build twine hatch-vcs
   ```

## Local build

The package is built with `python -m build` (no isolated venv required since
`hatchling` uses the dynamic version from git tags via `hatch-vcs`).

```bash
# Build wheel + sdist into dist/
python -m build --wheel --sdist --outdir dist/

# Verify the wheel contents
python -c "import zipfile; z=zipfile.ZipFile('dist/okf_wiki-*.whl'); print('\\n'.join(sorted(z.namelist())[:10]))"
```

Expected metadata in the wheel:

- `Name: okf-wiki`
- `Version: <git-derived>` (e.g. `0.1.dev9+g2a090e3.d20260827`)
- Entry points: `obsidian-wiki = obsidian_wiki.cli:main` AND `okf-wiki = obsidian_wiki.cli:main`

## Test on TestPyPI first (recommended)

```bash
# Upload to TestPyPI (NOT the real index)
python -m twine upload --repository testpypi dist/okf_wiki-*

# Verify install from TestPyPI in a fresh venv
python -m venv /tmp/okf-test
/tmp/okf-test/bin/pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ okf-wiki
/tmp/okf-test/bin/okf-wiki --help
```

## Publish to PyPI

Once the TestPyPI install verified:

```bash
# Configure the API token (one-time)
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-<your-token-here>

# Or use a project-scoped token in ~/.pypirc:
#   [pypi]
#   username = __token__
#   password = pypi-<your-token-here>

python -m twine upload dist/okf_wiki-*

# Verify
pip install okf-wiki
okf-wiki --help
obsidian-wiki --help   # legacy alias also works
```

## Versioning

Versions are derived from git tags via `hatch-vcs`:

- Tag `v2026.05.2` → package version `2026.5.2`
- Untagged commits → `0.1.dev<N>+g<short_sha>.d<YYYYMMDD>` (PEP 440 dev release)

To cut a release:

```bash
git tag v2026.5.2
git push --tags
# CI should pick this up and publish automatically
```

## GitHub Actions (recommended)

Add `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  push:
    tags: ["v*"]

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # hatch-vcs needs git history for version
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install build twine
      - run: python -m build --wheel --sdist
      - run: python -m twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

## Difference from upstream `obsidian-wiki`

| | upstream | okf-wiki (this fork) |
|---|---|---|
| PyPI name | `obsidian-wiki` | `okf-wiki` |
| Frontmatter | `category`, `summary`, `updated` | `type`, `description`, `generated` (OKF v0.2) |
| Source | ar9av/obsidian-wiki | bryce402/okf-wiki (fork) |
| Compatibility | Reads OKF pages as legacy | Writes OKF pages natively; reads legacy as fallback |

Installing `okf-wiki` alongside `obsidian-wiki` (e.g. in separate venvs) is
safe — they share no package internals.