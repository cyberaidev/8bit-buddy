# Contributing

Contributions are welcome. For a substantial new display backend or provider, open an issue first so
the event contract and security model can be agreed before implementation.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src
```

## Pull requests

- Keep hook handlers fail-open and fast.
- Do not parse vendor transcript files when a documented hook field exists.
- Add tests for every new lifecycle mapping.
- Preserve existing user hook configuration during install and uninstall.
- Do not add network services, telemetry, or cloud relays without an explicit threat model.
- Update the relevant documentation and `CHANGELOG.md`.

Small, focused pull requests are easiest to review.
