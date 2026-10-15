# CodeSentinel

CodeSentinel scans code changes for possible vulnerabilities. This project currently includes a research CPU baseline, a FastAPI service, a separate ONNX model service, a React dashboard, and local monitoring.

## Run the local stack

Requirements: Docker Desktop with Compose.

```sh
docker compose up --build
```

Open:

- API docs: http://localhost:8000/docs
- API health: http://localhost:8000/health
- Prometheus metrics: http://localhost:8000/metrics/
- Dashboard: http://localhost:3002
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (default local login: `admin` / `admin`; set `GRAFANA_ADMIN_PASSWORD` to change it)

The API calls the internal model service at `model-server:8001`; it is not exposed on the host. Prometheus scrapes both services, and the Grafana dashboard shows API latency, model inference latency, scan outcomes, and request errors.

Prometheus and Grafana ports are bound to localhost. The included Grafana dashboard is provisioned automatically. Stop the stack with `docker compose down`; add `-v` only when you also want to delete its local database and monitoring data.

## CI

The workflow in `.github/workflows/ci.yml` runs API and model tests, frontend lint/build, and a Docker image build on every push and pull request. Pushes to `main` can publish images to ECR and deploy to AWS after the OIDC role and repository variables are configured.

This directory is a standalone Git repository whose remote is `https://github.com/rudiously/MLOPS_CODE`.

## AWS staging

AWS deployment uses GitHub Actions OIDC and a single EC2 host managed through Systems Manager. Apply the infrastructure in `deploy/aws` with an AWS account that you control, then set the repository variables and secrets documented there. No long-lived AWS access keys are stored in GitHub.

## Model status

The checked-in CPU baseline is an experimental research artifact. Its held-out repository metrics are not strong enough for production or for blocking pull requests. The app marks the demo model accordingly and keeps GitHub checks neutral unless a validated non-demo model is configured.
