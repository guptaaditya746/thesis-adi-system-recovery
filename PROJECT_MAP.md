# Project map

## Backend

- `app/models/domain.py` — typed artifacts, run context, provenance, triples, evaluation
- `app/agents/` — question, ontology, SPARQL, retrieval, verifier sub-agents
- `app/tools/document.py` — structured PDF navigation/search tools
- `app/tools/registry.py` — extension point for additional toolsets
- `app/services/pdf.py` — PDF parsing + page/section workspace + FTS5
- `app/services/ontology.py` — seed loading, question-specific sub-ontology, controlled changes
- `app/services/sparql.py` — syntax validation + ontology preview execution
- `app/services/edc.py` — EDC-compatible Extract / Define / Canonicalize
- `app/services/validation.py` — RDF graph construction + SHACL
- `app/services/evaluation.py` — exact/normalized triple metrics + provenance/support metrics
- `app/services/context.py` — bounded context projection while full artifacts remain persisted
- `app/storage/` — immutable artifacts + in-memory streaming registry + persistent snapshots
- `app/api/main.py` — uploads, run creation, SSE events, artifacts, PDF serving

## Frontend

- `components/RunWorkbench.tsx` — upload/question/run workspace
- `components/PipelineTimeline.tsx` — stage progress
- `components/TripleGraph.tsx` — KG visualization
- Evidence view includes the original PDF beside retrieval artifacts
- Ontology, SPARQL, triple, evaluation and event inspection tabs

## Agent retrieval capabilities

Default shell commands: `ls`, `pwd`, `cat`, `rg`, `grep`, `find`, `sed`, `head`, `tail`, `wc`.

`bash` is supported but gated by `ENABLE_AGENT_BASH=true`.

Pydantic AI Harness `FileSystem` is root-scoped to the document workspace. Shell credentials are scrubbed using the Harness LLM-key patterns plus project secret patterns.
