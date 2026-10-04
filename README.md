# Secret Leak Scanner

A learning prototype that detects credential-like strings using configurable regular expressions, validators, and an entropy heuristic. It includes a Python CLI, a FastAPI service, SQLite persistence, and an Angular dashboard.

## Components

| Component | Implementation |
| --- | --- |
| Scanner | Rule definitions, JWT/PEM/length validators, allowlists, entropy checks |
| CLI | Local file scanning with binary and size limits |
| API | Scan requests, findings, rule management, reload operations, statistics |
| Persistence | SQLAlchemy models backed by SQLite |
| Dashboard | Angular pages for findings, scanning, rules, and summary data |
| Git integration | Optional hook samples; not installed automatically |

```text
backend/    Python service, scanner, CLI, rules, requirements
frontend/   Angular dashboard
hooks/      Optional pre-commit and pre-receive samples
docs/       Existing Chinese technical notes and validation record
tests/      Regression check for CLI configuration after directory changes
```

## Python setup

From the repository root:

```sh
uv venv .venv
uv pip install -r backend/requirements.txt
source .venv/bin/activate
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

The API creates a local `secrets.db`, which is ignored by Git. `/health` reports loaded rule counts. The CLI can be invoked from the root:

```sh
.venv/bin/python backend/cli.py --files path/to/a/local-test-file.txt
```

Exit code `1` indicates findings; `0` indicates no findings in the files processed. Inspect skipped-file handling before using this as an enforcement gate.

## Dashboard

The frontend requires a Node.js version compatible with its pinned Angular dependencies. This cleanup does not install Node.js on the Mac.

```sh
cd frontend
npm ci
npm run dev
```

The checked-in development configuration uses port `3000`; its API service targets `http://localhost:8000/api`.

## Current limits

- This is a prototype rather than a complete security control. Detection can produce false positives and false negatives.
- Stored findings use masks or hashes, but scan responses may still contain the raw matched string.
- API authentication is optional through `API_TOKEN`; the frontend does not yet attach that header.
- Hook samples enumerate staged filenames and scan working-tree files. They do not validate the exact staged blob.
- Notifications and some dashboard workflows remain placeholders.

See [existing Chinese technical notes](docs/project-notes.zh-CN.md) and [validation record](docs/validation.md). No production credentials or new deployment results are included.
