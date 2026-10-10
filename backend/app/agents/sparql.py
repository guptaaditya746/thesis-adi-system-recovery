from pydantic_ai import Agent

from app.agents.model_factory import build_model
from app.config import Settings
from app.models.domain import SPARQLArtifact


def build_sparql_agent(settings: Settings) -> Agent[None, SPARQLArtifact]:
    return Agent(
        build_model(settings), output_type=SPARQLArtifact,
        model_settings={"temperature": settings.llm_temperature, "max_tokens": settings.llm_max_tokens},
        instructions=(
            "Generate a SPARQL SELECT query over the provided active ontology to make the question's semantic intent "
            "explicit. Only reference prefixes/URIs shown in the ontology summary. The query is produced before document "
            "retrieval and therefore primarily captures ontology/query intent. Also emit semantic_terms and retrieval_hints."
        ),
    )
