from __future__ import annotations

import re

from app.models.domain import EvaluationResult, GoldAnnotation, VerifiedTriple


class EvaluationService:
    def evaluate(self, triples: list[VerifiedTriple], shacl_conforms: bool, gold: GoldAnnotation | None = None) -> EvaluationResult:
        result = EvaluationResult(
            provenance_coverage=(sum(bool(t.provenance.evidence_ids) for t in triples) / len(triples)) if triples else 0.0,
            supported_ratio=(sum(t.status == "supported" for t in triples) / len(triples)) if triples else 0.0,
            shacl_conformance=shacl_conforms,
        )
        if not gold or not gold.triples:
            result.notes.append("No gold triples supplied; exact/normalized P/R/F1 not computed.")
            return result
        pred_exact = {(t.triple.subject, t.triple.predicate, t.triple.object) for t in triples}
        gold_exact = {(t.subject, t.predicate, t.object) for t in gold.triples}
        ep, er, ef = self._prf(pred_exact, gold_exact)
        pred_norm = {tuple(self._norm(x) for x in row) for row in pred_exact}
        gold_norm = {tuple(self._norm(x) for x in row) for row in gold_exact}
        np, nr, nf = self._prf(pred_norm, gold_norm)
        return result.model_copy(update={
            "exact_precision": ep, "exact_recall": er, "exact_f1": ef,
            "normalized_precision": np, "normalized_recall": nr, "normalized_f1": nf,
        })

    @staticmethod
    def _prf(pred: set, gold: set) -> tuple[float, float, float]:
        tp = len(pred & gold)
        p = tp / len(pred) if pred else 0.0
        r = tp / len(gold) if gold else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        return p, r, f

    @staticmethod
    def _norm(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.lower()))
