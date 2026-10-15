# CodeSentinel Frontend

> Modern, AI-Powered Cybersecurity Dashboard & Vulnerability Detection Interface for the CodeSentinel Platform.

Built with **React 19**, **Vite**, **TypeScript**, **Tailwind CSS**, **Lucide Icons**, **Axios**, and **Recharts**.

---

## Features

- **Dashboard**: Real-time metrics from PostgreSQL (`GET /history`), vulnerability distribution charts, system health & latency monitor, and recent PR scan feeds.
- **AI Code Scanner**: Source code editor with line gutter, syntax assistance, sample vulnerability presets (SQLi, XSS, Buffer Overflow, Command Injection, Clean Code), and file upload support. Connects directly to `POST /score-file`.
- **Explainable Results (XAI)**: Visualizes model confidence, predicted CWE classifications with softmax probability bars, line-level occlusion attribution highlighting culprit tokens, and actionable mitigation advice.
- **GitHub PR Analysis**: Intercepts PR security regressions with `POST /analyze-pr`. Auto-parses GitHub PR URLs into `owner/repo` and `pr_number`, supporting custom diffs or GitHub App installations.
- **Scan History**: Full audit trail backed by PostgreSQL (`GET /history`) with repo search, severity filtering, pagination, and a "View Details" modal for deep inspection.
- **Security Reports**: Executive compliance reports mapping detected flaws to OWASP Top 10 and MITRE CWE categories with markdown/print export.
- **Platform Settings**: Configurable API Base URL, JWT bearer token support, and live backend ping diagnostics.

---

## Getting Started

### Prerequisites

- Node.js (v18+ or v20+)
- npm (v9+)
- Python 3.10+ / Docker (for the backend API)

### 1. Local Development

```powershell
cd codesentinel-frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

### 2. Configuration (.env)

The frontend communicates with the FastAPI backend through `VITE_API_BASE_URL`.

Create `.env` (or copy `.env.example`):

```bash
VITE_API_BASE_URL=http://localhost:8000
```

*Note: You can also adjust the backend URL directly in the **Settings** page in the UI at runtime.*

### 3. Production Build

```powershell
npm run build
npm run preview
```

---

## Docker Deployment

The frontend includes a multi-stage Docker build with Nginx:

```powershell
# Build standalone frontend image
docker build -t codesentinel-frontend .

# Run container on port 3000
docker run -p 3000:80 -e VITE_API_BASE_URL=http://localhost:8000 codesentinel-frontend
```

---

## Full Stack with Docker Compose

To launch the complete CodeSentinel platform (**FastAPI Backend + PostgreSQL + React Frontend**):

```powershell
# From the code_sentinal root directory:
docker compose up --build
```

- **Frontend Dashboard**: `http://localhost:3000`
- **FastAPI Backend & Swagger**: `http://localhost:8000/docs`
- **PostgreSQL Database**: `localhost:5432`
