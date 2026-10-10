from __future__ import annotations

import asyncio
from collections import defaultdict

from app.models.domain import ExperimentRun, RunEvent


class RunRegistry:
    def __init__(self) -> None:
        self.runs: dict[str, ExperimentRun] = {}
        self.queues: dict[str, list[asyncio.Queue[RunEvent]]] = defaultdict(list)

    def create(self, run: ExperimentRun) -> None:
        self.runs[run.id] = run

    def get(self, run_id: str) -> ExperimentRun:
        return self.runs[run_id]

    async def emit(self, event: RunEvent) -> None:
        run = self.runs[event.run_id]
        run.events.append(event)
        for queue in list(self.queues[event.run_id]):
            await queue.put(event)

    def subscribe(self, run_id: str) -> asyncio.Queue[RunEvent]:
        q: asyncio.Queue[RunEvent] = asyncio.Queue()
        self.queues[run_id].append(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue[RunEvent]) -> None:
        if q in self.queues.get(run_id, []):
            self.queues[run_id].remove(q)


registry = RunRegistry()
