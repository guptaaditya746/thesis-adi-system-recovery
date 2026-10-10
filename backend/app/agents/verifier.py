from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.agents.model_factory import build_model
from app.config import Settings


class TripleJudgment(BaseModel):
    triple_id: str
    status: str
    explanation: str
    inference_type: str = "direct"


class VerificationOutput(BaseModel):
    judgments: list[TripleJudgment] = Field(default_factory=list)


def build_verifier_agent(settings: Settings) -> Agent[None, VerificationOutput]:
    return Agent(
        build_model(settings), output_type=VerificationOutput,
        model_settings={"temperature": settings.llm_temperature, "max_tokens": settings.llm_max_tokens},
        instructions=(
            "Verify whether each candidate triple is supported by the cited evidence. Use only the supplied evidence. "
            "Status must be one of supported, weakly_supported, unsupported, conflicting. inference_type must be one of "
            "direct, aggregated, inferred, ontology_derived, uncertain. Give short observable explanations, not chain-of-thought."
        ),
    )
