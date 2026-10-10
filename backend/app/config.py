from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    frontend_origin: str = "http://localhost:3000"
    data_dir: Path = Path("./data")
    seed_ontology_path: Path = Path("./app/seed/dblp_minimal.ttl")

    litellm_api_base: str = "http://localhost:4000/v1"
    litellm_api_key: str = "replace-me"
    litellm_model: str = "openai/gpt-5.2"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    max_agent_steps: int = 16
    max_evidence_spans: int = 16
    max_evidence_chars: int = 30_000
    max_tool_output_chars: int = 20_000
    enable_agent_bash: bool = False
    agent_shell_timeout_seconds: float = 20.0

    pdf_max_pages: int = 200
    lexical_top_k: int = 12
    context_expansion_paragraphs: int = 2

    allow_ontology_extensions: bool = True
    shacl_strict: bool = False

    edc_upstream_path: str | None = None

    langtrace_api_key: str | None = None
    langtrace_api_host: str = "https://langtrace.ai/"
    enable_langtrace: bool = False
    enable_logfire: bool = False
    enable_llm_eval: bool = False

    shell_allowed_commands: list[str] = Field(
        default_factory=lambda: [
            "ls", "pwd", "cat", "rg", "grep", "find", "sed", "head", "tail", "wc",
        ]
    )

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "documents").mkdir(exist_ok=True)
        (self.data_dir / "runs").mkdir(exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
