from __future__ import annotations

from app.config import Settings
from app.models.domain import EvidenceBundle


class ContextManager:
    """Deterministic context budgeting. Full artifacts stay on disk; agents get bounded projections."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def bound_evidence(self, bundle: EvidenceBundle) -> EvidenceBundle:
        spans = []
        chars = 0
        for span in bundle.spans[: self.settings.max_evidence_spans]:
            remaining = self.settings.max_evidence_chars - chars
            if remaining <= 0:
                break
            text = span.text[:remaining]
            spans.append(span.model_copy(update={"text": text}))
            chars += len(text)
        return bundle.model_copy(update={"spans": spans})
