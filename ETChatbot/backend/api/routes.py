from __future__ import annotations

from io import StringIO

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from backend.models.schemas import ChatRequest, ChatResponse, Holding, PortfolioResponse
from backend.rag.orchestrator import Orchestrator
from backend.services.portfolio_store import portfolio_store


def build_router(orchestrator: Orchestrator) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.post("/portfolio/upload-csv", response_model=PortfolioResponse)
    async def upload_csv(
        file: UploadFile = File(...),
        user_id: str = Query(default="demo-user"),
    ) -> PortfolioResponse:
        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Please upload a CSV file.")

        content = await file.read()
        df = pd.read_csv(StringIO(content.decode("utf-8")))
        required = {"symbol", "allocation"}
        if not required.issubset(set(df.columns.str.lower())):
            raise HTTPException(status_code=400, detail="CSV must include symbol and allocation columns.")

        # Normalize column names for robust parsing.
        col_map = {c: c.lower() for c in df.columns}
        df = df.rename(columns=col_map)

        holdings: list[Holding] = []
        for _, row in df.iterrows():
            holdings.append(
                Holding(
                    symbol=str(row["symbol"]).strip().upper(),
                    quantity=float(row["quantity"]) if "quantity" in row and not pd.isna(row["quantity"]) else 0,
                    allocation=float(row["allocation"]),
                )
            )

        portfolio_store.set(user_id, holdings)
        return PortfolioResponse(
            user_id=user_id,
            holdings=holdings,
            total_allocation=round(sum(h.allocation for h in holdings), 2),
            message="Portfolio uploaded and stored in memory.",
        )

    @router.get("/portfolio/{user_id}", response_model=PortfolioResponse)
    def get_portfolio(user_id: str) -> PortfolioResponse:
        holdings = portfolio_store.get(user_id)
        return PortfolioResponse(
            user_id=user_id,
            holdings=holdings,
            total_allocation=round(sum(h.allocation for h in holdings), 2),
            message="Portfolio loaded.",
        )

    @router.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        holdings = portfolio_store.get(request.user_id)
        return orchestrator.run(request.query, holdings)

    @router.get("/ticker")
    def get_ticker() -> list[dict[str, str]]:
        import yfinance as yf
        symbols = {
            "NIFTY 50": "^NSEI",
            "SENSEX": "^BSESN",
            "RELIANCE": "RELIANCE.NS",
            "HDFC BANK": "HDFCBANK.NS",
            "TCS": "TCS.NS",
            "INFOSYS": "INFY.NS"
        }
        res = []
        for name, sym in symbols.items():
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="5d")
                if len(hist) >= 2:
                    prev_close = float(hist['Close'].iloc[-2])
                    curr = float(hist['Close'].iloc[-1])
                    change_pct = ((curr - prev_close) / prev_close) * 100
                    direction = "up" if change_pct >= 0 else "down"
                    sign = "+" if change_pct >= 0 else ""
                    res.append({
                        "name": name,
                        "price": f"{curr:,.2f}",
                        "change": f"{sign}{change_pct:.2f}%",
                        "direction": direction
                    })
                elif len(hist) == 1:
                    curr = float(hist['Close'].iloc[-1])
                    res.append({
                        "name": name,
                        "price": f"{curr:,.2f}",
                        "change": "+0.00%",
                        "direction": "up"
                    })
            except Exception:
                pass
        return res

    return router
