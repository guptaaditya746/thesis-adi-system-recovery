from __future__ import annotations

from collections.abc import Callable

from pydantic_ai import AbstractToolset

from app.agents.deps import AgentDeps

ToolsetFactory = Callable[[], AbstractToolset[AgentDeps]]


class ToolRegistry:
    """Extension point for project-specific agent tools."""

    def __init__(self) -> None:
        self._factories: dict[str, ToolsetFactory] = {}

    def register(self, name: str, factory: ToolsetFactory) -> None:
        self._factories[name] = factory

    def build(self, names: list[str]) -> list[AbstractToolset[AgentDeps]]:
        return [self._factories[name]() for name in names if name in self._factories]


registry = ToolRegistry()
