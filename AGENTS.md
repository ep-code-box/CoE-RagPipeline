# Repository Guidelines

## Project Structure & Module Organization
- Source: `main.py` (entry), `routers/` (FastAPI routes), `services/` (business logic), `models/` (Pydantic schemas), `core/` (app/server/logging), `utils/` (helpers).
- Analysis & RAG: `analyzers/` (code analysis), `chroma_db/` (local Chroma data), `output/` (generated docs/results), `cache/` and `logs/`.
- Config: `config/` (settings, prompts), `.env` (runtime secrets), `requirements.txt` (deps), `Dockerfile`, `run.sh`.
- DB Migrations: `dbmig/` (Alembic). Operational details in `../docs/OPERATIONS.md`.

## Architecture Overview
- FastAPI app: `main.py` creates app via `core.app_factory`; `core/server.py` runs Uvicorn.
- Routing: `routers/` defines endpoints and delegates to `services/`.
- Services: orchestrate analyzers, persistence, and vector ops.
- Models: `models/` Pydantic schemas; Config in `config/settings.py` via `.env`.
- Storage: Chroma in `chroma_db/`; generated artifacts in `output/`.

## Before You Change
- Run impact scan: `python scripts/impact.py --since origin/main`.
- Identify boundaries: keep HTTP logic in `routers/`, business in `services/`, data in `models/`.
- Check tokens/perf knobs in `config/settings.py` before heavy changes.
- Update `.env.example` if you add new env vars.

## Build, Test, and Development Commands
- Create venv: `python -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run locally: `bash run.sh` (loads `.env`, auto-installs, starts Uvicorn on 8001+)
- Alt run: `python main.py` or `uvicorn main:app --reload --port 8001`
- Lint: `flake8 .` and `pylint core routers services analyzers`
- Types: `mypy .`
- Security scan: `bandit -q -r .`
- Tests: `pytest -q` or with coverage `pytest --cov=services --cov=routers`
- Docker: `docker build -t coe-rag . && docker run --env-file .env -p 8001:8001 coe-rag`

## Change Impact Analysis
- Purpose: map Python imports to find transitive dependents and list affected API routes.
- Quick check (since main): `python scripts/impact.py --since origin/main`
- Specific files: `python scripts/impact.py --files services/vector.py routers/search.py`
- Outputs: console summary + JSON/DOT in `output/results/` (graph and report).

## Common Change Recipes
- Add API endpoint: create handler in `routers/<feature>.py`, call a thin function in `services/`, define request/response in `models/`. Add a `pytest` for the service and an `httpx` test for the route.
- Add service logic: new module in `services/`; avoid side effects in import time; inject config via `config.settings`.
- Extend analyzer: put detectors in `analyzers/<area>/`; keep I/O in services; write outputs to `output/`.
- DB migration: `alembic -c alembic.ini revision --autogenerate -m "feat: ..."` then `alembic -c alembic.ini upgrade head`. Document ops impact in PR.

## Coding Style & Naming Conventions
- Python 3, PEP 8, 4-space indent; prefer type hints and docstrings for public functions.
- Naming: `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep API boundaries thin in `routers/`; move logic to `services/`; keep DTOs in `models/`.

## Testing Guidelines
- Framework: `pytest` (+ `pytest-asyncio` for async, `httpx` for API tests).
- Location: create `tests/` mirroring package structure; filenames `test_*.py`.
- Coverage: prioritize `services/` and `routers/` critical paths; target meaningful assertions over blanket %.
- Example: `pytest tests/services/test_vector_search.py -q`.

## Commit & Pull Request Guidelines
- Commits: concise, imperative. Conventional Commits encouraged (e.g., `feat(routers): add vector search endpoint`).
- PRs: clear description, linked issues, API changes noted, before/after behavior, and any new env vars.
- Checks: run `flake8`, `pytest`, and `bandit` locally; include screenshots or curl examples for new endpoints.

## Security & Configuration Tips
- Never commit secrets; use `.env` and update `.env.example` when adding new keys (`OPENAI_API_KEY`, `SKAX_API_KEY`, `DATABASE_URL`, `CHROMA_*`).
- Default port is 8001; logs write to `./logs`. Large outputs go to `output/`—avoid committing generated artifacts.

## Operational Notes
- Logging: use `logging.getLogger(__name__)`; logs rotate in `./logs`.
- Token limits: respect `MAX_ANALYSIS_DATA_TOKENS`, `ENABLE_AUTO_CHUNKING`, and related settings in `config/settings.py` to avoid oversized prompts/results.
