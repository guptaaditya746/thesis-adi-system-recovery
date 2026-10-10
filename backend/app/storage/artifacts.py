from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.config import Settings

T = TypeVar("T", bound=BaseModel)


class ArtifactStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run_dir(self, run_id: str) -> Path:
        path = self.settings.data_dir / "runs" / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_model(self, run_id: str, name: str, value: BaseModel) -> str:
        path = self.run_dir(run_id) / f"{name}.json"
        path.write_text(value.model_dump_json(indent=2), encoding="utf-8")
        return str(path)

    def save_json(self, run_id: str, name: str, value: object) -> str:
        path = self.run_dir(run_id) / f"{name}.json"
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return str(path)

    def save_text(self, run_id: str, name: str, value: str, suffix: str = ".txt") -> str:
        path = self.run_dir(run_id) / f"{name}{suffix}"
        path.write_text(value, encoding="utf-8")
        return str(path)

    def load_json(self, run_id: str, name: str) -> dict:
        path = self.run_dir(run_id) / f"{name}.json"
        return json.loads(path.read_text(encoding="utf-8"))
