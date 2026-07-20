# Repository guidance

- Runtime code must remain Python 3.11+ standard-library-only unless a dependency has a compelling,
  documented benefit.
- Agent hooks are observability-only: catch failures, emit no behavioural stdout, and fail open.
- Never read transcript files when a documented lifecycle field provides the needed data.
- Preserve existing hook configuration and keep installation idempotent.
- Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` and
  `python3 -m compileall -q src` before handing off changes.
- Update tests and docs together when a vendor hook schema changes.
