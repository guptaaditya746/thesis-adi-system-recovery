# Architecture notes

## Controlled multi-agent graph

The system uses specialist agents rather than free-form agent chat:

1. QuestionAnalysisAgent
2. OntologyAgent
3. SPARQLAgent
4. RetrievalAgent
5. EDCService (Extract / Define / Canonicalize)
6. TripleVerifierAgent
7. deterministic RDF/SHACL validation
8. deterministic evaluation

Agents exchange typed Pydantic artifacts. Full PDFs and historical messages are not copied between agents.

## Retrieval

Retrieval is intentionally non-vector-first. It combines:
- document hierarchy tools
- SQLite FTS5
- Pydantic AI Harness FileSystem search/find/read
- Pydantic AI Harness Shell with rg/find/grep/etc.

This preserves an experimental boundary so embeddings can be added later as an ablation.

## Why SPARQL before retrieval?

The current thesis design uses SPARQL as an inspectable semantic query artifact derived from the question and active ontology. Before a document KG exists, it is executed against the ontology for validation/preview, while its semantic terms and retrieval hints inform document retrieval. After KG construction, a later experiment can re-run or transform it against the extracted graph.

## Provenance

Each EDC candidate triple must cite evidence IDs. Verified triples store those IDs plus document ID and inference type. The evidence objects retain page and extracted text. This is lightweight now and can later map to PROV-O.

## SHACL

SHACL is applied to the generated RDF graph using shapes derived from active ontology domain/range declarations. It answers “does this graph conform to structural constraints?”, not “was this ontology extension scientifically sensible?”.
