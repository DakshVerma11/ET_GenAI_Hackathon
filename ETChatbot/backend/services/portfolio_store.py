from __future__ import annotations

from backend.models.schemas import Holding


class PortfolioStore:
    def __init__(self) -> None:
        self._store: dict[str, list[Holding]] = {}

    def set(self, user_id: str, holdings: list[Holding]) -> None:
        self._store[user_id] = holdings

    def get(self, user_id: str) -> list[Holding]:
        return self._store.get(user_id, [])


portfolio_store = PortfolioStore()
