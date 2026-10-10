from pydantic_ai import Agent

from app.agents.model_factory import build_model
from app.config import Settings
from app.models.domain import QuestionAnalysis


def build_question_agent(settings: Settings) -> Agent[None, QuestionAnalysis]:
    return Agent(
        build_model(settings),
        output_type=QuestionAnalysis,
        model_settings={"temperature": settings.llm_temperature, "max_tokens": settings.llm_max_tokens},
        instructions=(
            "Analyze a user question about a scientific paper. Produce a compact observable plan, not hidden reasoning. "
            "Identify information needs, entities, concepts, and lexical retrieval terms."
        ),
    )
