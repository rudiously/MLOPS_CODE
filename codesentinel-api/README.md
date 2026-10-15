# CodeSentinel API

FastAPI serving and GitHub-App integration for the supplied `codesentinel_model` black-box package. It does not alter or duplicate model code.

## Layout

`app/api` exposes HTTP endpoints; `app/services` parses diffs and orchestrates scans; `app/github` verifies webhooks and calls GitHub; `app/db` holds SQLAlchemy models; `alembic` is the only source of schema DDL.

## Run locally

The supplied archive has been unpacked beside this directory as `../codesentinel-model`, so the Compose build installs it directly.

```powershell
cd codesentinel-api
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8000/docs`. Compose runs `alembic upgrade head` before starting the API. To use a managed Postgres later, set `DATABASE_URL` to its SQLAlchemy psycopg URL; no host is hardcoded in application code.

The Compose stack also starts Prometheus at `http://localhost:9090` and Grafana at
`http://localhost:3001` (local development login defaults to `admin` / `admin`).
The provisioned CodeSentinel dashboard includes API request rate and p95 latency,
model inference latency, scan volume, and 5xx error rate. Set
`GRAFANA_ADMIN_PASSWORD` before exposing Grafana beyond a local development
machine. The API exports metrics at `/metrics`.

For non-Docker development, install both packages and migrate:

```powershell
pip install -e ../codesentinel-model
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

## Endpoints

- `POST /score-file` accepts `code_snippet` and optional `language`.
- `POST /analyze-pr` accepts `repo`, `pr_number`, and either a unified `diff` or an `installation_id` to fetch it from GitHub.
- `GET /history` supports `repo`, `severity`, `date_from`, `date_to`, `page`, and `page_size`. Set `REQUIRE_DASHBOARD_AUTH=true` to require an HS256 bearer JWT signed with `JWT_SECRET`.
- `POST /webhooks/github` accepts GitHub `pull_request` events for `opened`, `synchronize`, and `reopened`.

GitHub checks are informational by default. Set `GITHUB_CHECKS_ENABLED=true` only
after installing a versioned model that has passed held-out-repository
evaluation; a demo or unknown model version always produces a neutral check.

## GitHub App setup

Set `WEBHOOK_SECRET`, `GITHUB_APP_ID`, and `GITHUB_PRIVATE_KEY` (newlines may be written as `\\n`). Configure the webhook URL as `/webhooks/github`, subscribe to Pull requests, and grant the GitHub App **Pull requests: Read**, **Checks: Read & write**, and **Issues: Read & write** permissions. Relevant webhooks fetch the PR diff, persist the scan, and post a concise PR comment. Check runs are neutral by default; enable merge blocking only after real-model evaluation and installation of a non-demo model version.

## Tests

`pytest` covers endpoint success/validation paths, signature verification, a clean Alembic migration, and an end-to-end diff scan with `model_predict` mocked. The real model is never reimplemented or fine-tuned here.
