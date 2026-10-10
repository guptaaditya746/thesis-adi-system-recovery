from pydantic_ai import Agent, FunctionToolset, RunContext

from app.agents.deps import AgentDeps
from app.agents.model_factory import build_model
from app.config import Settings
from app.models.domain import OntologyProposal, QuestionAnalysis


def build_ontology_agent(settings: Settings) -> Agent[AgentDeps, OntologyProposal]:
    tools = FunctionToolset[AgentDeps]()

    @tools.tool
    def search_seed_ontology(ctx: RunContext[AgentDeps], terms: list[str]) -> list[dict]:
        """Search the seed ontology for relevant classes/properties.

        Args:
            terms: Concept or relation terms from the question.
        """
        return [x.model_dump() for x in ctx.deps.ontology.search(terms)]

    @tools.tool
    def inspect_seed_inventory(ctx: RunContext[AgentDeps], limit: int = 120) -> list[dict]:
        """Inspect seed ontology elements when search terms are insufficient.

        Args:
            limit: Maximum elements to return.
        """
        return [x.model_dump() for x in ctx.deps.ontology.inventory(limit)]

    return Agent(
        build_model(settings), deps_type=AgentDeps, output_type=OntologyProposal, toolsets=[tools],
        model_settings={"temperature": settings.llm_temperature, "max_tokens": settings.llm_max_tokens},
        instructions=(
            "Select a minimal question-specific ontology from the seed ontology. You may propose additions when the seed "
            "cannot express a required concept. Prefer seed terms when semantically appropriate. Generated URIs must use "
            "https://example.org/thesis/generated/. Explain choices only in decision_summary."
        ),
    )
