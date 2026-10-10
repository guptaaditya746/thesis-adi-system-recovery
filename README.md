# Thesis ADI System

Research prototype for question-driven knowledge graph construction from scientific PDFs. It combines a FastAPI/Python backend with a Next.js/TypeScript frontend. See `PROJECT_MAP.md` and `docs/ARCHITECTURE.md` for the pipeline and structure.

## Run locally

1. Create local configuration: `cp .env.example .env` and fill in credentials on your machine. The published example has credential values blanked.
2. Backend: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev,eval,observability]" && uvicorn app.api.main:app --reload --port 8000`.
3. Frontend in a second terminal: `cd frontend && npm install && npm run dev`.
4. Open `http://localhost:3000`.

Requirements include Python 3.12+ and Node.js compatible with the Next.js app. The compose file provides the container-based setup. Keep local datasets and runtime artifacts out of Git; see `BACKUP_MANIFEST.md`.
