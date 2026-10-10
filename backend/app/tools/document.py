from __future__ import annotations

from pydantic_ai import FunctionToolset, RunContext

from app.agents.deps import AgentDeps


def build_document_toolset() -> FunctionToolset[AgentDeps]:
    tools = FunctionToolset[AgentDeps]()

    @tools.tool
    def list_sections(ctx: RunContext[AgentDeps]) -> list[dict]:
        """List scientific document sections with page ranges."""
        return [
            {"id": s.id, "heading": s.heading, "page_start": s.page_start, "page_end": s.page_end}
            for s in ctx.deps.document.sections
        ]

    @tools.tool
    def read_section(ctx: RunContext[AgentDeps], section_id: str) -> str:
        """Read a section by ID.

        Args:
            section_id: ID returned by list_sections.
        """
        return ctx.deps.retrieval.read_section(ctx.deps.document, section_id)

    @tools.tool
    def read_page(ctx: RunContext[AgentDeps], page: int) -> str:
        """Read one PDF page's extracted text.

        Args:
            page: One-based page number.
        """
        return ctx.deps.retrieval.read_page(ctx.deps.document, page)

    @tools.tool
    def search_document(ctx: RunContext[AgentDeps], query: str, limit: int = 8) -> list[dict]:
        """Lexically search the paper using SQLite FTS5, not embeddings.

        Args:
            query: Search terms or phrase.
            limit: Maximum evidence candidates.
        """
        return [x.model_dump() for x in ctx.deps.retrieval.search(ctx.deps.document, query, limit)]

    @tools.tool
    def expand_evidence(ctx: RunContext[AgentDeps], evidence: dict, paragraphs: int = 2) -> dict:
        """Expand context around an evidence candidate.

        Args:
            evidence: EvidenceSpan-shaped dictionary from search_document.
            paragraphs: Neighbor paragraph count.
        """
        from app.models.domain import EvidenceSpan
        span = EvidenceSpan.model_validate(evidence)
        return ctx.deps.retrieval.expand(ctx.deps.document, span, paragraphs).model_dump()

    return tools
