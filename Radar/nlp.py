"""
NLP Processor — powered by Claude API or Ollama

This is the signal-finding intelligence layer, NOT a summarizer.

What it does for each raw event:
1. Classifies the event type and extracts structured facts
2. Scores sentiment (0–100) and labels it
3. Detects semantic anomalies vs sector baseline
4. Generates a short, actionable headline + 2-sentence summary
5. Suggests 4 analysis talking points with sentiment tags
6. Computes an NLP anomaly sigma (how unusual is this language?)

All outputs are structured JSON — no free-text parsing required downstream.
"""
import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import aiohttp
except ImportError:
    aiohttp = None

from settings import settings

logger = logging.getLogger(__name__)

# Lazy-init clients so the app starts even without API keys
_anthropic_client: Optional[anthropic.AsyncAnthropic] = None
_aiohttp_session: Optional[aiohttp.ClientSession] = None


def get_anthropic_client() -> Optional[anthropic.AsyncAnthropic]:
    global _anthropic_client
    if anthropic is None:
        return None
    if _anthropic_client is None and settings.anthropic_api_key:
        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


async def get_aiohttp_session() -> aiohttp.ClientSession:
    global _aiohttp_session
    if _aiohttp_session is None or _aiohttp_session.closed:
        _aiohttp_session = aiohttp.ClientSession()
    return _aiohttp_session


@dataclass
class NLPResult:
    headline: str
    summary: str
    sentiment_label: str          # "Strongly Bullish" | "Bullish" | "Neutral" | "Bearish" | "Strongly Bearish"
    sentiment_score: float        # 0–100
    nlp_anomaly_sigma: float      # how many σ from typical event in this category
    analysis_points: list[dict]   # [{label, value, sentiment}] × 4
    signal_type_override: Optional[str]   # if NLP reclassifies the event type
    raw_response: str             # for debugging


SYSTEM_PROMPT = """You are the NLP scoring engine for Opportunity Radar, an AI investment intelligence platform for Indian equity markets (NSE/BSE).

Your job is NOT to summarize news. Your job is to find signals — anomalies, inflection points, and hidden patterns that most investors will miss.

For each market event, you will output a structured JSON object (and ONLY that — no preamble, no markdown fences).

Rules:
- Be specific to Indian markets: use INR, refer to SEBI, NSE, BSE, FY notation, crores/lakhs
- Sentiment scores: 0=maximally bearish, 50=neutral, 100=maximally bullish
- NLP anomaly sigma: how many standard deviations from "typical" for this event type. 0=normal, 1=slightly unusual, 2=notable, 3+=very rare
- Analysis points: factual observations with clear investment relevance, NOT generic filler
- Headlines: under 80 characters, present tense, specific
- Summary: exactly 2 sentences. First sentence = what happened. Second sentence = why it matters for the stock.

Output schema (strict JSON, no other text):
{
  "headline": "string (≤80 chars)",
  "summary": "string (2 sentences)",
  "sentiment_label": "Strongly Bullish|Bullish|Neutral|Bearish|Strongly Bearish",
  "sentiment_score": number (0-100),
  "nlp_anomaly_sigma": number (0-4),
  "analysis_points": [
    {"label": "string", "value": "string", "sentiment": "positive|negative|neutral"},
    {"label": "string", "value": "string", "sentiment": "positive|negative|neutral"},
    {"label": "string", "value": "string", "sentiment": "positive|negative|neutral"},
    {"label": "string", "value": "string", "sentiment": "positive|negative|neutral"}
  ],
  "signal_type_override": null | "filing|bulk|insider|result|nlp"
}"""


async def score_event(event_source: str, ticker: str, raw_data: dict) -> NLPResult:
    """
    Score a raw event through the NLP pipeline.
    Supports both Ollama and Anthropic APIs.
    Falls back to heuristic scoring if both APIs are unavailable.
    """
    prompt = _build_prompt(event_source, ticker, raw_data)

    # Try configured LLM provider
    logger.info(f"[NLP] Using LLM provider: {settings.llm_provider}")
    
    if settings.llm_provider == "ollama":
        logger.info(f"[NLP] Attempting Ollama at {settings.ollama_base_url} with model {settings.ollama_model}")
        result = await _call_ollama(prompt, event_source, ticker, raw_data)
        if result:
            logger.info(f"[NLP] ✓ Ollama scored {ticker} successfully")
            return result
        logger.warning(f"[NLP] ✗ Ollama failed for {ticker}, trying heuristic")
    
    elif settings.llm_provider == "anthropic":
        logger.info(f"[NLP] Attempting Anthropic Claude API")
        result = await _call_anthropic(prompt, event_source, ticker, raw_data)
        if result:
            logger.info(f"[NLP] ✓ Claude scored {ticker} successfully")
            return result
        logger.warning(f"[NLP] ✗ Claude failed for {ticker}, trying heuristic")

    # Fallback to heuristic if no provider available
    logger.warning(f"[NLP] No working LLM provider (configured: {settings.llm_provider}) — using heuristic NLP fallback")
    return _heuristic_score(event_source, ticker, raw_data)


async def _call_anthropic(prompt: str, event_source: str, ticker: str, raw_data: dict) -> Optional[NLPResult]:
    """Call Anthropic Claude API (fallback if Ollama unavailable)."""
    if not settings.anthropic_api_key or anthropic is None:
        logger.debug("[CLAUDE] Anthropic API not configured or module unavailable")
        return None

    try:
        logger.info(f"[CLAUDE] Fallback: Calling Anthropic Claude API for {ticker}")
        client = get_anthropic_client()
        if not client:
            logger.error("[CLAUDE] Failed to initialize Anthropic client")
            return None
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
        logger.info(f"[CLAUDE] ✓ Successfully analyzed {ticker} via fallback")
        return _parse_response(raw_text, event_source, ticker, raw_data)

    except Exception as e:
        logger.error(f"[CLAUDE] ✗ Anthropic API error for {ticker}: {e}")
        return None


async def _call_ollama(prompt: str, event_source: str, ticker: str, raw_data: dict) -> Optional[NLPResult]:
    """Call Ollama local LLM API (OpenAI-compatible format)."""
    if not settings.ollama_base_url or not settings.ollama_model:
        logger.error("[OLLAMA] Configuration missing: base_url or model")
        return None

    try:
        logger.info(f"[OLLAMA] Calling {settings.ollama_base_url} with model {settings.ollama_model} for {ticker}")
        
        session = await get_aiohttp_session()
        url = f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
        }
        if settings.ollama_api_key:
            headers["Authorization"] = f"Bearer {settings.ollama_api_key}"
            logger.debug(f"[OLLAMA] Using API key (length: {len(settings.ollama_api_key)})")

        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1000,
            "temperature": 0.7,
        }

        logger.debug(f"[OLLAMA] POST {url}")
        async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status != 200:
                error_msg = await resp.text()
                logger.error(f"[OLLAMA] ✗ HTTP {resp.status} for {ticker}: {error_msg[:200]}")
                return None

            logger.debug(f"[OLLAMA] ✓ HTTP 200 received for {ticker}")
            data = await resp.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            logger.info(f"[OLLAMA] ✓ Successfully analyzed {ticker} (response: {len(raw_text)} chars)")
            return _parse_response(raw_text, event_source, ticker, raw_data)

    except asyncio.TimeoutError:
        logger.error(f"[OLLAMA] ✗ Timeout for {ticker}")
        return None
    except Exception as e:
        logger.error(f"[OLLAMA] ✗ Exception for {ticker}: {type(e).__name__}: {e}")
        return None


def _build_prompt(source: str, ticker: str, data: dict) -> str:
    """Build the scoring prompt from the raw event data."""
    lines = [f"Event type: {source}", f"Stock: {ticker}"]

    if source == "filings":
        lines += [
            f"Company: {data.get('company', '')}",
            f"Filing type: {data.get('filing_type', '')}",
            f"Description: {data.get('description', '')}",
            f"Date: {data.get('date', '')}",
        ]
    elif source == "bulk":
        lines += [
            f"Company: {data.get('company', '')}",
            f"Deal type: {data.get('deal_kind', 'bulk').upper()} DEAL",
            f"Client: {data.get('client_name', '')}",
            f"Action: {data.get('buy_sell', '')}",
            f"Quantity: {data.get('quantity', 0):,.0f} shares @ ₹{data.get('price', 0):,.2f}",
            f"Value: ₹{data.get('value_cr', 0):.2f} crores",
            f"Promoter entity: {data.get('looks_like_promoter', False)}",
            f"FII entity: {data.get('looks_like_fii', False)}",
        ]
    elif source == "insider":
        lines += [
            f"Company: {data.get('company', '')}",
            f"Insider: {data.get('person_name', '')} ({data.get('person_category', '')})",
            f"Transaction: {data.get('transaction_type', '')}",
            f"Quantity: {data.get('quantity', 0):,.0f} shares @ ₹{data.get('price', 0):,.2f}",
            f"Value: ₹{data.get('value_cr', 0):.2f} crores",
            f"Senior executive: {data.get('is_senior_executive', False)}",
        ]

    return "\n".join(lines)


def _parse_response(raw: str, source: str, ticker: str, data: dict) -> NLPResult:
    """Parse Claude's JSON response into a NLPResult."""
    # Strip any accidental markdown fences
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        obj = json.loads(clean)
        return NLPResult(
            headline=obj.get("headline", f"{ticker} activity detected"),
            summary=obj.get("summary", ""),
            sentiment_label=obj.get("sentiment_label", "Neutral"),
            sentiment_score=float(obj.get("sentiment_score", 50)),
            nlp_anomaly_sigma=float(obj.get("nlp_anomaly_sigma", 0)),
            analysis_points=obj.get("analysis_points", []),
            signal_type_override=obj.get("signal_type_override"),
            raw_response=raw,
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"NLP response parse error for {ticker}: {e} — using fallback")
        return _heuristic_score(source, ticker, data)


def _heuristic_score(source: str, ticker: str, data: dict) -> NLPResult:
    """
    Deterministic fallback scoring when Claude API is unavailable.
    Uses rule-based heuristics to produce a reasonable score.
    """
    score = 50.0
    sigma = 0.5

    if source == "insider":
        value_cr = data.get("value_cr", 0)
        is_senior = data.get("is_senior_executive", False)
        score = min(75 + (value_cr * 2) + (10 if is_senior else 0), 95)
        sigma = min(1.0 + value_cr * 0.3, 3.0)
        headline = f"{ticker}: {data.get('person_name', 'Insider')} buys ₹{value_cr:.1f}Cr"
        summary = (
            f"{data.get('person_category', 'Insider')} {data.get('person_name', '')} acquired "
            f"₹{value_cr:.2f} crores worth of shares in {ticker}. "
            f"Insider buying — especially by senior management — is a high-conviction positive signal."
        )
        sentiment = "Bullish" if score >= 65 else "Neutral"
        analysis_points = [
            {"label": "Buyer category", "value": data.get("person_category", "Insider"), "sentiment": "positive"},
            {"label": "Trade value", "value": f"₹{value_cr:.2f} Cr", "sentiment": "positive"},
            {"label": "Price paid", "value": f"₹{data.get('price', 0):,.2f}", "sentiment": "neutral"},
            {"label": "Senior exec", "value": "Yes" if is_senior else "No", "sentiment": "positive" if is_senior else "neutral"},
        ]

    elif source == "bulk":
        value_cr = data.get("value_cr", 0)
        buy_sell = data.get("buy_sell", "")
        is_buy = "BUY" in buy_sell.upper()
        is_promoter = data.get("looks_like_promoter", False)
        score = (70 if is_buy else 30) + (10 if is_promoter else 0)
        sigma = min(0.8 + value_cr * 0.05, 2.5)
        deal_kind = data.get("deal_kind", "bulk").capitalize()
        headline = f"{ticker}: {deal_kind} deal ₹{value_cr:.0f}Cr {'BUY' if is_buy else 'SELL'} by {data.get('client_name', 'entity')[:30]}"
        summary = (
            f"A {deal_kind.lower()} deal of ₹{value_cr:.2f} crores was executed for {ticker}. "
            f"{'Large buy-side activity suggests accumulation by an informed investor.' if is_buy else 'Large sell-side activity warrants monitoring for further distribution.'}"
        )
        sentiment = ("Bullish" if is_buy and score >= 65 else ("Bearish" if not is_buy else "Neutral"))
        analysis_points = [
            {"label": "Deal type", "value": f"{deal_kind} {'Buy' if is_buy else 'Sell'}", "sentiment": "positive" if is_buy else "negative"},
            {"label": "Value", "value": f"₹{value_cr:.2f} Cr", "sentiment": "neutral"},
            {"label": "Promoter entity", "value": "Yes" if is_promoter else "No", "sentiment": "positive" if is_promoter and is_buy else "neutral"},
            {"label": "FII entity", "value": "Yes" if data.get("looks_like_fii") else "No", "sentiment": "neutral"},
        ]

    elif source == "filings":
        filing_type = data.get("filing_type", "")
        high_signal_types = {"Financial Results", "Acquisitions/Mergers", "Buyback", "Open Offer", "QIP", "Rights Issue"}
        is_high = any(t in filing_type for t in high_signal_types)
        score = 65.0 if is_high else 50.0
        sigma = 1.2 if is_high else 0.5
        headline = f"{ticker}: {filing_type} filing — {data.get('description', '')[:50]}"
        summary = (
            f"{ticker} filed a {filing_type} with NSE. "
            f"{'This is a potentially material disclosure requiring further analysis.' if is_high else 'Routine regulatory filing — monitor for material disclosures.'}"
        )
        sentiment = "Bullish" if is_high else "Neutral"
        analysis_points = [
            {"label": "Filing type", "value": filing_type, "sentiment": "positive" if is_high else "neutral"},
            {"label": "Signal relevance", "value": "High" if is_high else "Routine", "sentiment": "positive" if is_high else "neutral"},
            {"label": "Date", "value": data.get("date", ""), "sentiment": "neutral"},
            {"label": "Exchange", "value": "NSE", "sentiment": "neutral"},
        ]
    else:
        headline = f"{ticker}: New {source} event detected"
        summary = f"A {source} event was detected for {ticker}. Manual review recommended."
        sentiment = "Neutral"
        analysis_points = []

    return NLPResult(
        headline=headline,
        summary=summary,
        sentiment_label=sentiment,
        sentiment_score=score,
        nlp_anomaly_sigma=sigma,
        analysis_points=analysis_points,
        signal_type_override=None,
        raw_response="[heuristic fallback]",
    )