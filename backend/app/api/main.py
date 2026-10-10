from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from app.config import get_settings
from app.models.domain import ExperimentRun, StartRunRequest
from app.orchestration.pipeline import PipelineOrchestrator
from app.services.observability import configure_observability
from app.services.pdf import PDFService
from app.storage.registry import registry

settings = get_settings()
configure_observability(settings)
pdf_service = PDFService(settings)
orchestrator = PipelineOrchestrator(settings, registry)

app = FastAPI(title="Thesis ADI Research Pipeline", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "thesis-adi-backend"}


@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...)) -> dict:
    filename = file.filename or "upload.pdf"
    if file.content_type not in {"application/pdf", "application/octet-stream"} and not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")
    content = await file.read()
    try:
        doc = pdf_service.ingest(filename, content)
        return doc.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/documents/{document_id}")
def get_document(document_id: str) -> dict:
    try:
        return pdf_service.load(document_id).model_dump(mode="json")
    except FileNotFoundError as exc:
        raise HTTPException(404, "Document not found") from exc


@app.get("/api/documents/{document_id}/pdf")
def get_pdf(document_id: str) -> FileResponse:
    doc = pdf_service.load(document_id)
    return FileResponse(Path(doc.workspace) / "source.pdf", media_type="application/pdf", filename=doc.filename)


@app.post("/api/runs")
async def start_run(request: StartRunRequest) -> dict:
    try:
        pdf_service.load(request.document_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Document not found") from exc
    run = ExperimentRun(document_id=request.document_id, question=request.question)
    registry.create(run)
    orchestrator.store.save_model(run.id, "run_snapshot", run)
    asyncio.create_task(orchestrator.run(run, request.gold))
    return run.model_dump(mode="json")


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict:
    try:
        return registry.get(run_id).model_dump(mode="json")
    except KeyError:
        snapshot = settings.data_dir / "runs" / run_id / "run_snapshot.json"
        if snapshot.exists():
            return json.loads(snapshot.read_text(encoding="utf-8"))
        raise HTTPException(404, "Run not found")


@app.get("/api/runs/{run_id}/artifacts/{name}")
def get_artifact(run_id: str, name: str):
    if not name.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Invalid artifact name")
    run_dir = settings.data_dir / "runs" / run_id
    candidates = [run_dir / f"{name}.json", run_dir / f"{name}.txt", run_dir / f"{name}.ttl"]
    path = next((p for p in candidates if p.exists()), None)
    if not path:
        raise HTTPException(404, "Artifact not found")
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return FileResponse(path)


@app.get("/api/runs/{run_id}/events")
async def stream_events(run_id: str):
    try:
        run = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(404, "Run not found") from exc

    async def generator():
        for event in run.events:
            yield f"data: {event.model_dump_json()}\n\n"
        queue = registry.subscribe(run_id)
        try:
            while True:
                if run.status in {"completed", "failed"} and queue.empty():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            registry.unsubscribe(run_id, queue)

    return StreamingResponse(generator(), media_type="text/event-stream")
