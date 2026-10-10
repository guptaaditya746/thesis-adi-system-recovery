from __future__ import annotations

from app.config import Settings


def configure_observability(settings: Settings) -> None:
    if settings.enable_langtrace and settings.langtrace_api_key:
        try:
            from langtrace_python_sdk import langtrace
            langtrace.init(api_key=settings.langtrace_api_key, api_host=settings.langtrace_api_host)
        except Exception:
            pass
    if settings.enable_logfire:
        try:
            import logfire
            logfire.configure()
            logfire.instrument_pydantic_ai()
        except Exception:
            pass
