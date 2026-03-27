from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MarketStore:
    def __init__(self, data_path: Path) -> None:
        self._data_path = data_path
        self.fundamentals = self._load_by_symbol("fundamentals.json")
        self.technicals = self._load_by_symbol("technicals.json")
        self.documents = self._load_raw("documents.json")

    def _load_raw(self, name: str) -> list[dict[str, Any]]:
        with (self._data_path / name).open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def _load_by_symbol(self, name: str) -> dict[str, dict[str, Any]]:
        rows = self._load_raw(name)
        return {row["symbol"]: row for row in rows}

    @property
    def symbols(self) -> list[str]:
        return list(self.fundamentals.keys())
