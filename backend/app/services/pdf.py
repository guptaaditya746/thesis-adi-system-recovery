from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz

from app.config import Settings
from app.models.domain import DocumentSection, ScientificDocument, new_id


class PDFService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def ingest(self, filename: str, content: bytes) -> ScientificDocument:
        sha = hashlib.sha256(content).hexdigest()
        doc_id = new_id("doc")
        workspace = self.settings.data_dir / "documents" / doc_id
        workspace.mkdir(parents=True, exist_ok=True)
        pdf_path = workspace / "source.pdf"
        pdf_path.write_bytes(content)

        pdf = fitz.open(stream=content, filetype="pdf")
        if len(pdf) > self.settings.pdf_max_pages:
            raise ValueError(f"PDF has {len(pdf)} pages; max is {self.settings.pdf_max_pages}")

        pages: list[str] = []
        for i, page in enumerate(pdf):
            text = page.get_text("text") or ""
            pages.append(text)
            (workspace / f"page_{i + 1:04d}.txt").write_text(text, encoding="utf-8")

        joined = "\n\n".join(f"=== PAGE {i+1} ===\n{t}" for i, t in enumerate(pages))
        (workspace / "document.txt").write_text(joined, encoding="utf-8")

        sections = self._infer_sections(pages)
        sections_dir = workspace / "sections"
        sections_dir.mkdir(exist_ok=True)
        for section in sections:
            (sections_dir / f"{section.id}.txt").write_text(section.text, encoding="utf-8")

        doc = ScientificDocument(
            id=doc_id,
            filename=filename,
            sha256=sha,
            page_count=len(pages),
            sections=sections,
            workspace=str(workspace),
        )
        (workspace / "document.json").write_text(doc.model_dump_json(indent=2), encoding="utf-8")
        self._build_fts(workspace, pages)
        return doc

    def load(self, document_id: str) -> ScientificDocument:
        path = self.settings.data_dir / "documents" / document_id / "document.json"
        return ScientificDocument.model_validate_json(path.read_text(encoding="utf-8"))

    def _infer_sections(self, pages: list[str]) -> list[DocumentSection]:
        # Lightweight structure extraction. GROBID/Docling can replace this service later.
        heading_re = re.compile(r"^(?:\d+(?:\.\d+)*\s+)?[A-Z][A-Za-z0-9 ,:/()\-]{2,80}$")
        sections: list[DocumentSection] = []
        current_heading = "Document"
        current_text: list[str] = []
        start_page = 1
        counter = 0

        def flush(end_page: int) -> None:
            nonlocal counter, current_text
            text = "\n".join(current_text).strip()
            if not text:
                return
            counter += 1
            sections.append(DocumentSection(
                id=f"sec_{counter:04d}", heading=current_heading, level=1,
                page_start=start_page, page_end=end_page, text=text,
            ))
            current_text = []

        for pageno, text in enumerate(pages, start=1):
            for line in text.splitlines():
                candidate = line.strip()
                if heading_re.match(candidate) and len(candidate.split()) <= 10:
                    if len("\n".join(current_text)) > 400:
                        flush(pageno)
                        current_heading = candidate
                        start_page = pageno
                        continue
                current_text.append(line)
        flush(len(pages))
        if not sections:
            sections.append(DocumentSection(
                id="sec_0001", heading="Document", level=1, page_start=1,
                page_end=max(1, len(pages)), text="\n".join(pages),
            ))
        return sections

    def _build_fts(self, workspace: Path, pages: list[str]) -> None:
        import sqlite3
        db = sqlite3.connect(workspace / "search.sqlite3")
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(page UNINDEXED, text)")
        db.execute("DELETE FROM pages")
        db.executemany("INSERT INTO pages(page, text) VALUES (?, ?)", [(i + 1, t) for i, t in enumerate(pages)])
        db.commit()
        db.close()
