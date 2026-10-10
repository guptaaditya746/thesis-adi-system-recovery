from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic_ai import Agent

from app.agents.model_factory import build_model
from app.config import Settings
from app.models.domain import (
    CandidateTriple,
    CanonicalTriple,
    EvidenceBundle,
    OntologyElement,
    RelationDefinition,
)


class ExtractionOutput(__import__('pydantic').BaseModel):
    triples: list[CandidateTriple]


class DefinitionOutput(__import__('pydantic').BaseModel):
    definitions: list[RelationDefinition]


@dataclass
class EDCResult:
    open_triples: list[CandidateTriple]
    definitions: list[RelationDefinition]
    canonical_triples: list[CanonicalTriple]


class EDCService:
    """Lightweight EDC-compatible Extract → Define → Canonicalize pipeline.

    It follows EDC's decomposition while replacing embedding schema retrieval with the
    question-specific active ontology and typed LLM outputs.
    """

    def __init__(self, settings: Settings):
        model = build_model(settings)
        self.extract_agent = Agent(
            model,
            output_type=ExtractionOutput,
            model_settings={"temperature": settings.llm_temperature, "max_tokens": settings.llm_max_tokens},
            instructions=(
                "Extract factual semantic triples from the provided evidence only. "
                "Every triple must cite one or more supplied evidence IDs. Do not invent facts. "
                "Use concise relation phrases; candidate ontology relations are hints, not permission to hallucinate."
            ),
        )
        self.define_agent = Agent(
            model,
            output_type=DefinitionOutput,
            model_settings={"temperature": settings.llm_temperature, "max_tokens": settings.llm_max_tokens},
            instructions=(
                "Define each relation in general subject-to-object terms. Preserve directionality. "
                "Return one definition per distinct relation."
            ),
        )

    async def run(self, bundle: EvidenceBundle, relations: list[OntologyElement]) -> EDCResult:
        relation_text = "\n".join(
            f"- {r.label} ({r.uri}): {r.description or ''} domain={r.domain or '?'} range={r.range or '?'}"
            for r in relations
        )
        evidence_text = "\n\n".join(f"[{s.id}] page {s.page}: {s.text}" for s in bundle.spans)
        extraction = await self.extract_agent.run(
            f"Candidate ontology relations:\n{relation_text}\n\nEvidence:\n{evidence_text}"
        )
        open_triples = extraction.output.triples
        distinct = sorted({t.predicate for t in open_triples})
        definitions: list[RelationDefinition] = []
        if distinct:
            definition_result = await self.define_agent.run(
                "Relations:\n" + "\n".join(distinct) + "\n\nEvidence context:\n" + evidence_text[:12000]
            )
            definitions = definition_result.output.definitions
        canonical = [self._canonicalize(t, relations, definitions) for t in open_triples]
        return EDCResult(open_triples=open_triples, definitions=definitions, canonical_triples=canonical)

    def _canonicalize(
        self,
        triple: CandidateTriple,
        relations: list[OntologyElement],
        definitions: list[RelationDefinition],
    ) -> CanonicalTriple:
        pred_norm = self._norm(triple.predicate)
        exact = next((r for r in relations if self._norm(r.label) == pred_norm), None)
        if exact:
            return CanonicalTriple(
                subject=triple.subject, predicate=exact.label, object=triple.object,
                predicate_uri=exact.uri, evidence_ids=triple.evidence_ids,
                canonicalization="exact", confidence=0.95,
            )
        # Token-overlap canonicalization is deterministic and inspectable; LLM semantic matching can be added as an ablation.
        p_tokens = set(pred_norm.split())
        scored: list[tuple[float, OntologyElement]] = []
        for rel in relations:
            r_tokens = set(self._norm(rel.label + " " + (rel.description or "")).split())
            denom = max(1, len(p_tokens | r_tokens))
            scored.append((len(p_tokens & r_tokens) / denom, rel))
        scored.sort(key=lambda x: -x[0])
        if scored and scored[0][0] >= 0.2:
            score, rel = scored[0]
            return CanonicalTriple(
                subject=triple.subject, predicate=rel.label, object=triple.object,
                predicate_uri=rel.uri, evidence_ids=triple.evidence_ids,
                canonicalization="ontology_match", confidence=min(0.9, 0.55 + score),
            )
        return CanonicalTriple(
            subject=triple.subject, predicate=triple.predicate, object=triple.object,
            evidence_ids=triple.evidence_ids, canonicalization="open_relation", confidence=0.55,
        )

    @staticmethod
    def _norm(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.lower()))
