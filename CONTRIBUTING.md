# Contributing

Use Python 3.12. Create a branch, add tests, and run:

```bash
ruff format --check .
ruff check .
mypy sniper
pytest -q
```

Never use a funded wallet or real credential in tests, fixtures, logs, screenshots, issues, or pull requests. Security reports belong in the private process described in [SECURITY.md](SECURITY.md), not a public issue.
