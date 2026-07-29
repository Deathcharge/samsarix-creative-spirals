# Contributing

Contributions should preserve the product boundary: a local-first, reviewable transformation and
export tool. Network publishing, credential handling, AI providers, scheduling, or analytics need
a documented product decision and threat model before implementation.

## Setup

Prerequisites: Python 3.10+ and Git.

```bash
python -m venv .venv
```

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
python -m pip install -r requirements-dev.txt
```

## Required checks

```bash
python -m black --check samsarix_creative_spirals tests examples
python -m flake8 samsarix_creative_spirals tests examples
python -m mypy
python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing
python -m build
```

Tests must cover user-visible success and failure behavior. Keep coverage at or above the configured
90% threshold. Do not relax a check or suppress a failure solely to make CI pass.

## Change guidelines

- Keep public API additions small and typed.
- Reject ambiguous configuration rather than guessing.
- Preserve stdout for successful/machine-readable output and stderr for errors.
- Keep filesystem operations inside explicit commands and generated bundle paths.
- Add no runtime dependency without documenting why the standard library is insufficient.
- Update the README, API reference, changelog, and productization record when behavior changes.
- Never add real credentials, customer content, fabricated output, or production endpoints to
  examples or fixtures.

## Commits and pull requests

Use focused commits with an imperative subject such as `fix: preserve links during truncation`.
A pull request should explain the user problem, behavior change, verification commands, security or
privacy impact, and any deferred work. CI must pass on every supported matrix version before merge.

## License

Contributions are made under MPL-2.0; see `LICENSE`. Preserve applicable copyright and SPDX
notices. The license does not grant rights to Samsarix trademarks; see `TRADEMARKS.md`.

By submitting a contribution, you represent that you have the right to submit it under MPL-2.0.
Large or strategically significant contributions may require a separate contributor agreement in
the future, but none is currently required. Contact `contact@samsarix.com` with licensing questions.
