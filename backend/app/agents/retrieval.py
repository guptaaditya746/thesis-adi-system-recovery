from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai_harness import FileSystem, Shell
from pydantic_ai_harness.shell import LLM_API_KEY_ENV_PATTERNS

from app.agents.deps import AgentDeps
from app.agents.model_factory import build_model
from app.config import Settings
from app.models.domain import EvidenceBundle
from app.tools.document import build_document_toolset


def build_retrieval_agent(settings: Settings, workspace: str) -> Agent[AgentDeps, EvidenceBundle]:
    allowed = list(settings.shell_allowed_commands)
    if settings.enable_agent_bash:
        allowed.append("bash")

    capabilities = [
        FileSystem(root_dir=Path(workspace), max_read_lines=1200, max_search_results=250, max_find_results=250),
        Shell(
            cwd=Path(workspace),
            allowed_commands=allowed,
            default_timeout=settings.agent_shell_timeout_seconds,
            max_output_chars=settings.max_tool_output_chars,
            denied_env_patterns=[*LLM_API_KEY_ENV_PATTERNS, "*TOKEN*", "*SECRET*", "*PASSWORD*", "LANGTRACE_*"],
        ),
    ]
    return Agent(
        build_model(settings), deps_type=AgentDeps, output_type=EvidenceBundle,
        toolsets=[build_document_toolset()], capabilities=capabilities,
        model_settings={"temperature": settings.llm_temperature, "max_tokens": settings.llm_max_tokens},
        instructions=(
            "You are the agentic retrieval specialist. Retrieve evidence from the scientific paper using tools. "
            "Do not use embeddings. Use section navigation, lexical search, rg/find/grep when useful, page reads, and context "
            "expansion. Return only evidence actually observed. Prefer a small high-recall evidence set. Every span must preserve "
            "document_id/page/text/retrieval metadata. Stop when the evidence is sufficient for downstream EDC extraction."
        ),
    )
