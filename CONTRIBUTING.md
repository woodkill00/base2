# Contributing

Thank you for contributing to Base2!

## Getting Started

- Install Python 3.12 (see .python-version)
- Install Node 18 (see react-app/.nvmrc)
- Copy .env.example to .env and adjust values
- Start stack: `docker compose -f local.docker.yml up -d`

## Development Flow

- Install pre-commit hooks: `pip install pre-commit && pre-commit install`
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
