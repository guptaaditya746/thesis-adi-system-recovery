from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.litellm import LiteLLMProvider

from app.config import Settings


def build_model(settings: Settings) -> OpenAIChatModel:
    provider = LiteLLMProvider(api_base=settings.litellm_api_base, api_key=settings.litellm_api_key)
    return OpenAIChatModel(settings.litellm_model, provider=provider)
