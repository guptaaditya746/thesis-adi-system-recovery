# Adding agent tools

There are three extension levels.

1. Document tool functions: add a typed function to `backend/app/tools/document.py`.
2. New toolset: create a `FunctionToolset[AgentDeps]` factory and register it in `backend/app/tools/registry.py`.
3. Harness capabilities: add Pydantic AI Harness capabilities (e.g. CodeMode, Skills, Exa) to a specific agent only when justified.

Keep privileges narrow. Retrieval tools should read the document workspace; ontology mutation should go through `OntologyService`; persistent artifact writes should remain orchestrator-owned.
