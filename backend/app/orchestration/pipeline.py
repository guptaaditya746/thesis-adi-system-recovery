from __future__ import annotations

import asyncio
from pathlib import Path

from app.agents.deps import AgentDeps
from app.agents.ontology import build_ontology_agent
from app.agents.question import build_question_agent
from app.agents.retrieval import build_retrieval_agent
from app.agents.sparql import build_sparql_agent
from app.agents.verifier import build_verifier_agent
from app.config import Settings
from app.models.domain import (
    ExperimentRun,
    GoldAnnotation,
    OntologyProposal,
    PipelineContext,
    ProvenanceRecord,
    RunEvent,
    SPARQLArtifact,
    VerifiedTriple,
)
from app.services.context import ContextManager
from app.services.edc import EDCService
from app.services.evaluation import EvaluationService
from app.services.ontology import OntologyService
from app.services.pdf import PDFService
from app.services.retrieval import RetrievalService
from app.services.sparql import SPARQLService
from app.services.validation import GraphValidationService
from app.storage.artifacts import ArtifactStore
from app.storage.registry import RunRegistry


class PipelineOrchestrator:
    def __init__(self, settings: Settings, registry: RunRegistry):
        self.settings = settings
        self.registry = registry
        self.pdf = PDFService(settings)
        self.retrieval = RetrievalService(settings)
        self.ontology = OntologyService(settings)
        self.sparql = SPARQLService()
        self.context_manager = ContextManager(settings)
        self.edc = EDCService(settings)
        self.validator = GraphValidationService()
        self.evaluator = EvaluationService()
        self.store = ArtifactStore(settings)

    async def run(self, run: ExperimentRun, gold: GoldAnnotation | None = None) -> None:
        try:
            run.status = "running"
            doc = self.pdf.load(run.document_id)
            ctx = PipelineContext(run_id=run.id, document_id=doc.id, question=run.question)
            run.context = ctx
            deps = AgentDeps(settings=self.settings, document=doc, retrieval=self.retrieval, ontology=self.ontology)

            await self._emit(run, "question", "started", "Question analysis", "Normalizing question and information needs")
            qa = (await build_question_agent(self.settings).run(run.question)).output
            self.store.save_model(run.id, "question_analysis", qa)
            ctx.question_analysis_ref = "question_analysis"
            await self._emit(run, "question", "completed", "Question analyzed", qa.decision_summary, "question_analysis")

            await self._emit(run, "ontology", "started", "Ontology agent", "Searching DBLP seed and proposing a minimal active ontology")
            onto_prompt = f"Question: {run.question}\nQuestion analysis: {qa.model_dump_json(indent=2)}"
            proposal: OntologyProposal = (await build_ontology_agent(self.settings).run(onto_prompt, deps=deps)).output
            onto_path = self.store.run_dir(run.id) / "active_subontology.ttl"
            subontology = self.ontology.build_subontology(proposal, onto_path)
            self.store.save_model(run.id, "ontology_proposal", proposal)
            self.store.save_model(run.id, "subontology", subontology)
            ctx.ontology_ref = "subontology"
            await self._emit(
                run, "ontology", "completed", "Active sub-ontology created",
                f"{len(subontology.selected_elements)} selected seed elements, {len(subontology.applied_changes)} changes",
                "subontology",
            )

            await self._emit(run, "sparql", "started", "SPARQL agent", "Generating ontology-aware query intent")
            ontology_text = Path(subontology.turtle_path).read_text(encoding="utf-8")[:18000]
            sparql_prompt = f"Question: {run.question}\n\nActive ontology:\n{ontology_text}"
            sparql_artifact: SPARQLArtifact = (await build_sparql_agent(self.settings).run(sparql_prompt)).output
            sparql_artifact = self.sparql.validate_and_preview(sparql_artifact, subontology)
            self.store.save_model(run.id, "sparql", sparql_artifact)
            ctx.sparql_ref = "sparql"
            await self._emit(
                run, "sparql", "completed", "SPARQL prepared",
                "Valid" if sparql_artifact.valid else f"Validation issue: {sparql_artifact.validation_error}", "sparql",
            )

            await self._emit(run, "retrieval", "started", "Retrieval agent", "Navigating the PDF with lexical/file/shell tools")
            retrieval_agent = build_retrieval_agent(self.settings, doc.workspace)
            retrieval_prompt = (
                f"Question: {run.question}\n\nQuestion analysis: {qa.model_dump_json()}\n\n"
                f"SPARQL intent: {sparql_artifact.model_dump_json()}\n"
                "Retrieve sufficient evidence for EDC triple extraction."
            )
            bundle = (await retrieval_agent.run(retrieval_prompt, deps=deps)).output
            bundle = self.context_manager.bound_evidence(bundle)
            self.store.save_model(run.id, "evidence", bundle)
            ctx.evidence_ref = "evidence"
            await self._emit(run, "retrieval", "completed", "Evidence selected", f"{len(bundle.spans)} evidence spans", "evidence")

            await self._emit(run, "edc", "started", "EDC pipeline", "Extract → Define → Canonicalize")
            relations = self.ontology.relation_catalog(subontology)
            edc_result = await self.edc.run(bundle, relations)
            self.store.save_json(run.id, "edc_open_triples", [x.model_dump() for x in edc_result.open_triples])
            self.store.save_json(run.id, "edc_definitions", [x.model_dump() for x in edc_result.definitions])
            self.store.save_json(run.id, "canonical_triples", [x.model_dump() for x in edc_result.canonical_triples])
            ctx.triples_ref = "canonical_triples"
            await self._emit(run, "edc", "completed", "EDC canonicalization complete", f"{len(edc_result.canonical_triples)} candidate triples", "canonical_triples")

            await self._emit(run, "verification", "started", "Triple verifier", "Checking evidence support for every triple")
            verifier = build_verifier_agent(self.settings)
            evidence_by_id = {s.id: s for s in bundle.spans}
            verify_payload = []
            for t in edc_result.canonical_triples:
                verify_payload.append({
                    "triple": t.model_dump(),
                    "evidence": [evidence_by_id[e].model_dump() for e in t.evidence_ids if e in evidence_by_id],
                })
            judgments = (await verifier.run(str(verify_payload))).output.judgments if verify_payload else []
            by_id = {j.triple_id: j for j in judgments}
            verified: list[VerifiedTriple] = []
            for t in edc_result.canonical_triples:
                j = by_id.get(t.id)
                status = j.status if j and j.status in {"supported", "weakly_supported", "unsupported", "conflicting"} else "weakly_supported"
                inference = j.inference_type if j and j.inference_type in {"direct", "aggregated", "inferred", "ontology_derived", "uncertain"} else "uncertain"
                verified.append(VerifiedTriple(
                    triple=t,
                    status=status,
                    explanation=j.explanation if j else "No verifier judgment returned.",
                    provenance=ProvenanceRecord(
                        triple_id=t.id, document_id=doc.id, evidence_ids=t.evidence_ids,
                        inference_type=inference, method="agentic_retrieval+edc",
                    ),
                ))
            self.store.save_json(run.id, "verified_triples", [x.model_dump() for x in verified])
            run.final_triples = verified
            await self._emit(run, "verification", "completed", "Triples verified", f"{sum(t.status == 'supported' for t in verified)} supported", "verified_triples")

            await self._emit(run, "validation", "started", "RDF / SHACL validation", "Constructing graph and checking ontology-derived shapes")
            validation = self.validator.validate([v.triple for v in verified if v.status != "unsupported"], subontology)
            self.store.save_model(run.id, "validation", validation)
            ctx.validation_ref = "validation"
            await self._emit(run, "validation", "completed", "Validation complete", f"SHACL conforms: {validation.shacl_conforms}", "validation")

            await self._emit(run, "evaluation", "started", "Evaluation", "Computing deterministic pipeline metrics")
            evaluation = self.evaluator.evaluate(verified, validation.shacl_conforms, gold)
            self.store.save_model(run.id, "evaluation", evaluation)
            run.evaluation = evaluation
            ctx.evaluation_ref = "evaluation"
            await self._emit(run, "evaluation", "completed", "Evaluation complete", f"Provenance coverage {evaluation.provenance_coverage:.0%}", "evaluation")

            run.status = "completed"
            await self._emit(run, "run", "completed", "Run completed", "All pipeline stages finished")
        except Exception as exc:
            run.status = "failed"
            run.error = f"{type(exc).__name__}: {exc}"
            await self._emit(run, "run", "failed", "Run failed", run.error)

    async def _emit(self, run: ExperimentRun, stage: str, status: str, title: str, detail: str = "", artifact_id: str | None = None) -> None:
        run.context.current_stage = stage if run.context else stage
        await self.registry.emit(RunEvent(
            run_id=run.id, type=f"{stage}.{status}", stage=stage, status=status,
            title=title, detail=detail, artifact_id=artifact_id,
        ))
        self.store.save_model(run.id, "run_snapshot", run)
