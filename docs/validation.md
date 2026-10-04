# Validation record

Date: 2026-10-04. Cleanup baseline commit: `128b9b3ec44e16a42453a6eab1b50baff1616a65`.

## Preservation and structure

- 32 retained blobs are unchanged at their current paths.
- 32 generated build/cache/executable entries are omitted from the current tree; the baseline history remains available.
- New documents and required configuration/path adaptations are recorded in the cleanup pull request. No existing source history is rewritten.
- Current filenames have no case-insensitive collisions. Markdown file links and generated-output ignore rules are checked before publication.

## Checks and limits

- Python 3.14.8 with PyYAML 6.0.3 in an isolated environment: `python -m unittest discover -s tests -v` passed two cases.
- The cases invoke the CLI from a parent directory with a local filename, proving that a backend-specific custom rule blocks a synthetic sentinel and that the backend allowlist suppresses it.
- Both optional hook samples passed `bash -n`. They were not installed or tested as security enforcement hooks.
- Frontend JSON is valid; package metadata and dependency lock entries remain identical. Dashboard source bytes are preserved.
- No Node.js/Angular build, browser/API integration, deployed service, real credential scanning, or production security validation was performed.

