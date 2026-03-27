from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _load_json(filename: str) -> Any:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as fp:
        return json.load(fp)


class DataStore:
    def __init__(self) -> None:
        self.fundamentals: dict[str, dict[str, Any]] = {
            item["symbol"]: item for item in _load_json("fundamentals.json")
        }
        self.technicals: dict[str, dict[str, Any]] = {
            item["symbol"]: item for item in _load_json("technicals.json")
        }
        self.documents: list[dict[str, Any]] = _load_json("documents.json")

    @property
    def symbol_universe(self) -> list[str]:
        return list(self.fundamentals.keys())
