# Contributing

First off — **thank you** for considering a contribution!  This project is small and
welcoming, and contributions of all sizes are appreciated: bug reports, documentation fixes,
new features, and questions are all valid ways to help.

## Ways to contribute

- 🐛 **Report a bug** — open an issue with steps to reproduce.
- 💡 **Suggest a feature** — open an issue describing the use case.
- 📖 **Improve the docs** — typos, unclear steps, missing details. (Docs PRs are the easiest
  way to get started.)
- 🔧 **Send a pull request** — fix a bug or add a feature.

If you're not sure whether something is wanted, **open an issue first** and ask. We'd rather
help you aim before you invest time.

## Good first issues

Look for issues labelled [`good first issue`](https://github.com/GraafG/powerplatform-markitdown-function/labels/good%20first%20issue).
Improving documentation, adding a sample flow, or extending test coverage are all great
starting points.

## Development setup

You need:

- **Python 3.11** (the function targets 3.11; newer works for local edits)
- **Azure Functions Core Tools v4** — `func`
- **Azure CLI** — `az` (only needed to deploy)

```bash
# clone your fork
git clone https://github.com/<you>/powerplatform-markitdown-function.git
cd powerplatform-markitdown-function/src

# create a virtual environment and install deps
python -m venv .venv
. .venv/Scripts/activate        # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
pip install -r ../requirements-dev.txt

# run the function locally (from src/)
func start
```

To run locally you'll also want a `local.settings.json` in `src/` (it is git-ignored):

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true"
  }
}
```

`/api/convert` works fully offline — no external services or credentials are required.

## Making a change

1. **Fork** the repo and create a branch: `git checkout -b fix/short-description`
2. Make your change. Keep it focused — one logical change per PR.
3. **Test it.** At minimum, run the function locally and exercise the endpoint you touched
   (e.g. `POST` a small PDF/DOCX to `/api/convert`).
   Also run the automated checks from the repo root:
   ```bash
   pytest -q
   python -m py_compile src/function_app.py
   ```
4. Update **documentation** if behaviour changed.
5. **Commit** with a clear message (see below) and open a **pull request** against `main`.
6. Describe *what* and *why* in the PR description; link any related issue.

## Commit messages

Use clear, imperative messages, e.g.:

```
Add retry to markitdown conversion

Large PDFs occasionally hit transient errors; retry up to 3x with backoff.
```

## Code style

- Python: follow **PEP 8**. Keep functions small and readable.
- Only comment code that genuinely needs clarification.
- Don't introduce new tools/linters in a PR without discussing it first.

## Code of Conduct

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE) that covers this project.
