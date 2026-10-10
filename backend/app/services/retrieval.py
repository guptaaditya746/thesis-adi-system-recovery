from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from app.config import Settings
from app.models.domain import EvidenceSpan, ScientificDocument


class RetrievalService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def search(self, doc: ScientificDocument, query: str, limit: int | None = None) -> list[EvidenceSpan]:
        limit = limit or self.settings.lexical_top_k
        db = sqlite3.connect(Path(doc.workspace) / "search.sqlite3")
        db.row_factory = sqlite3.Row
        safe_query = self._fts_query(query)
        rows = db.execute(
            "SELECT page, text, bm25(pages) AS score FROM pages WHERE pages MATCH ? ORDER BY score LIMIT ?",
            (safe_query, limit),
        ).fetchall()
        db.close()
        spans: list[EvidenceSpan] = []
        for row in rows:
            snippet = self._best_paragraph(row["text"], query)
            spans.append(EvidenceSpan(
                document_id=doc.id,
                page=int(row["page"]),
                text=snippet,
                retrieval_method="sqlite_fts5",
                retrieval_query=query,
                score=float(-row["score"]),
            ))
        return spans

    def read_page(self, doc: ScientificDocument, page: int) -> str:
        if page < 1 or page > doc.page_count:
            raise ValueError("page out of range")
        return (Path(doc.workspace) / f"page_{page:04d}.txt").read_text(encoding="utf-8")

    def read_section(self, doc: ScientificDocument, section_id: str) -> str:
        return (Path(doc.workspace) / "sections" / f"{section_id}.txt").read_text(encoding="utf-8")

    def expand(self, doc: ScientificDocument, span: EvidenceSpan, paragraphs: int = 2) -> EvidenceSpan:
        page = self.read_page(doc, span.page)
        paras = [p.strip() for p in re.split(r"\n\s*\n", page) if p.strip()]
        if not paras:
            return span
        idx = max(range(len(paras)), key=lambda i: self._overlap(paras[i], span.text))
        lo, hi = max(0, idx - paragraphs), min(len(paras), idx + paragraphs + 1)
        return span.model_copy(update={"text": "\n\n".join(paras[lo:hi]), "retrieval_method": span.retrieval_method + "+expand"})

    @staticmethod
    def _fts_query(query: str) -> str:
        terms = re.findall(r"[A-Za-z0-9_\-]{3,}", query)
        return " OR ".join(f'"{t}"' for t in terms[:12]) or '"scientific"'

    @staticmethod
    def _best_paragraph(text: str, query: str) -> str:
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paras:
            return text[:4000]
        q = set(re.findall(r"\w+", query.lower()))
        return max(paras, key=lambda p: len(q & set(re.findall(r"\w+", p.lower()))))[:5000]

    @staticmethod
    def _overlap(a: str, b: str) -> int:
        return len(set(re.findall(r"\w+", a.lower())) & set(re.findall(r"\w+", b.lower())))
