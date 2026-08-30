# Contributing

Thank you for contributing!

## Getting Started

- Install Python 3.12 (see .python-version)
- Install Node 24.20.0 (see react-app/.nvmrc)
- Copy .env.example to .env and adjust values
- Start stack: `docker compose -f development.docker.yml up -d`

## Development Flow

- Install pre-commit hooks: `pip install pre-commit && pre-commit install`
- Install Python deps (local venv):
  - API: `python -m pip install -r requirements-dev-api.txt`
  - Django: `python -m pip install -r requirements-dev-django.txt`
- Lint/format: `pre-commit run --all-files`
- Backend tests: run via deploy script or locally with `pytest`
- Frontend tests: `cd react-app && npm run test:ci`

## Branching

- Feature branches from `main`
- Open PR with description, screenshots (if UI), and tests

## Commit Style

- Write clear, descriptive commits
- Reference issues where relevant

## Code Review

- CI must pass (lint, tests, coverage)
- Keep PRs focused and reasonably small
