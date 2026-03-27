"""
VideoGen AI Engine — Groq Backend
Generates structured JSON video scripts using Groq chat completions
(same API pattern as ETChatbot, llama-3.3-70b-versatile).
"""

import os
import json
import requests
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"


def _get_groq_key() -> str | None:
    load_dotenv()
    key = os.getenv("GROQ_API_KEY", "").strip()
    return key if key and key != "YOUR_GROQ_API_KEY_HERE" else None


def _groq_chat(system: str, user: str, temperature: float = 0.3, max_tokens: int = 2048) -> str:
    """
    Call Groq chat completions and return the assistant message content.
    Mirrors the pattern used in ETChatbot/backend/rag/hf_client.py.
    """
    api_key = _get_groq_key()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in VideoGen/.env")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":    GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "temperature": temperature,
        "max_tokens":  max_tokens,
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text[0:300]}")

    return response.json()["choices"][0]["message"]["content"].strip()


def _parse_json_response(text: str) -> dict:
    """Strip any markdown fences and parse JSON."""
    clean = text.replace("```json", "").replace("```", "").strip()
    # Take only from first '{' to avoid leading prose
    start = clean.find("{")
    if start != -1:
        clean = clean[start:]
    return json.loads(clean)


# ─────────────────────────────────────────────────────────────
# SCENE NORMALIZER  (unchanged from original)
# ─────────────────────────────────────────────────────────────
def _normalize_scene_payload(data: Dict, expected_scenes: int = 7) -> Dict:
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    normalized: List[Dict] = []

    for idx, scene in enumerate(scenes[:expected_scenes], start=1):
        if not isinstance(scene, dict):
            scene = {}
        title        = scene.get("title") or scene.get("scene_title") or f"Scene {idx}"
        caption      = scene.get("caption") or "MARKET UPDATE"
        voiceover    = scene.get("voiceover") or "Market update is being generated."
        on_screen    = scene.get("on_screen_text")
        if not isinstance(on_screen, list):
            on_screen = [caption]
        captions     = scene.get("captions")
        if not isinstance(captions, list):
            captions = [caption]
        data_used    = scene.get("data_used")
        if not isinstance(data_used, list):
            data_used = []

        normalized.append({
            "scene_number":  idx,
            "scene_title":   title,
            "title":         title,
            "visual":        scene.get("visual", "Financial broadcast visual"),
            "on_screen_text": on_screen,
            "voiceover":     voiceover,
            "caption":       caption,
            "captions":      captions,
            "data_used":     data_used,
        })

    while len(normalized) < expected_scenes:
        idx = len(normalized) + 1
        normalized.append({
            "scene_number":  idx,
            "scene_title":   f"Scene {idx}",
            "title":         f"Scene {idx}",
            "visual":        "Financial broadcast visual",
            "on_screen_text": ["MARKET UPDATE"],
            "voiceover":     "Market update is being generated.",
            "caption":       "MARKET UPDATE",
            "captions":      ["MARKET UPDATE"],
            "data_used":     [],
        })

    data["scenes"] = normalized
    return data


def _fallback_script(expected_scenes: int, reason: str) -> Dict:
    return _normalize_scene_payload({
        "video_title": "Indian Stock Market Daily Update",
        "scenes":      [],
        "meta":        {"source": "fallback", "reason": reason},
    }, expected_scenes=expected_scenes)


# ─────────────────────────────────────────────────────────────
# PUBLIC FUNCTIONS
# ─────────────────────────────────────────────────────────────
def generate_macro_script(market_dashboard: dict) -> dict:
    """Legacy helper — generate a compact 7-scene storyboard from raw dashboard data."""
    dashboard_json = json.dumps(market_dashboard, indent=2)

    system = (
        "You are a professional financial news anchor writing data-rich daily briefings "
        "for Indian retail investors. Respond ONLY with valid JSON — no markdown, no prose."
    )
    user = f"""Generate a 7-scene market video script JSON using the schema below.

MARKET DATA:
{dashboard_json}

REQUIREMENTS:
1. Cite exact numbers (e.g. "Nifty 50 closed at 22,480, up 0.6%").
2. Cover sectors from the Sectors data — top gainers AND losers.
3. Tone: energetic, professional.
4. Each scene needs a 3-5 word caption for on-screen text.

SCHEMA:
{{
  "video_title": "Indian Stock Market Daily Update",
  "scenes": [
    {{"scene_number": 1, "scene_title": "Intro", "caption": "MARKET UPDATE", "voiceover": "..."}},
    {{"scene_number": 2, "scene_title": "Major Indices", "caption": "MIXED CLOSING", "voiceover": "..."}},
    {{"scene_number": 3, "scene_title": "Market Trend", "caption": "VIX STABILIZES", "voiceover": "..."}},
    {{"scene_number": 4, "scene_title": "Sector Winners", "caption": "TOP GAINERS", "voiceover": "..."}},
    {{"scene_number": 5, "scene_title": "Sector Losers", "caption": "SECTORS DRAGGING", "voiceover": "..."}},
    {{"scene_number": 6, "scene_title": "Key Insight", "caption": "KEY INSIGHT", "voiceover": "..."}},
    {{"scene_number": 7, "scene_title": "Closing", "caption": "SUBSCRIBE", "voiceover": "..."}}
  ]
}}"""

    try:
        text = _groq_chat(system, user)
        data = _parse_json_response(text)

        # Log for debugging
        os.makedirs("output", exist_ok=True)
        with open("output/groq_log.txt", "w", encoding="utf-8") as f:
            f.write("=== GROQ USER PROMPT ===\n" + user + "\n\n")
            f.write("=== GROQ RESPONSE ===\n" + text + "\n")

        if "scenes" not in data or len(data["scenes"]) < 7:
            data["scenes"] = [{"voiceover": "Data processing error on scene."}] * 7
        return data

    except Exception as e:
        print(f"Groq AI Error: {e}")
        return {"error": str(e), "prompt": user}


def generate_structured_script(
    market_dashboard: Dict, scene_blueprint: List[Dict], expected_scenes: int = 7
) -> Dict:
    """Generate strict scene JSON aligned to a scene blueprint via Groq."""
    dashboard_json = json.dumps(market_dashboard, indent=2)
    blueprint_json = json.dumps(scene_blueprint, indent=2)

    system = (
        "You are a professional financial news anchor creating short-form video scripts. "
        "Respond ONLY with valid JSON — no markdown, no extra text."
    )
    user = f"""Create a market video script with exactly {expected_scenes} scenes.

MARKET DATA:
{dashboard_json}

SCENE BLUEPRINT:
{blueprint_json}

REQUIREMENTS:
1. Return a JSON object with keys "video_title" and "scenes".
2. "scenes" must have exactly {expected_scenes} objects.
3. Each scene must include: scene_number, title, visual, on_screen_text (array),
   voiceover, captions (array), data_used (array), caption.
4. Use exact values and percentages from market data.
5. If winners/losers are unavailable, use neutral language.
6. Tone: energetic, professional. Respond with valid JSON only."""

    try:
        text = _groq_chat(system, user)
        data = _parse_json_response(text)
        data = _normalize_scene_payload(data, expected_scenes=expected_scenes)
        data.setdefault("meta", {})["source"] = "groq"
        return data
    except Exception as e:
        print(f"Groq structured script error: {e}")
        return _fallback_script(expected_scenes, str(e))


def generate_structured_script_with_prompt(
    market_dashboard: Dict, scene_blueprint: List[Dict], expected_scenes: int = 7
) -> Tuple[str, Dict, Dict]:
    """
    Generate script and return (prompt, script_json, status_dict).
    Mirrors the original Gemini signature for drop-in compatibility with app.py.
    """
    dashboard_json = json.dumps(market_dashboard, indent=2)
    blueprint_json = json.dumps(scene_blueprint, indent=2)

    system = (
        "You are a professional financial news anchor creating short-form video scripts. "
        "Respond ONLY with valid JSON — no markdown, no extra text."
    )
    user_prompt = f"""Create a market video script with exactly {expected_scenes} scenes.

MARKET DATA:
{dashboard_json}

SCENE BLUEPRINT:
{blueprint_json}

REQUIREMENTS:
1. Return a JSON object with keys "video_title" and "scenes".
2. "scenes" must have exactly {expected_scenes} objects.
3. Each scene: scene_number, title, visual, on_screen_text (array), voiceover,
   captions (array), data_used (array), caption.
4. Use exact values and percentages from market data.
5. Neutral language when data is missing.
6. Tone: energetic, professional. Valid JSON only — no markdown."""

    try:
        text = _groq_chat(system, user_prompt)
        data = _parse_json_response(text)
        data = _normalize_scene_payload(data, expected_scenes=expected_scenes)
        data.setdefault("meta", {})["source"] = "groq"

        # Log
        os.makedirs("output", exist_ok=True)
        with open("output/groq_log.txt", "w", encoding="utf-8") as f:
            f.write("=== GROQ SYSTEM ===\n" + system + "\n\n")
            f.write("=== GROQ USER PROMPT ===\n" + user_prompt + "\n\n")
            f.write("=== GROQ RESPONSE ===\n" + text + "\n")

        return (user_prompt, data, {"source": "groq", "status": "success"})

    except RuntimeError as e:
        # Key missing — surface clearly so Streamlit can show it
        msg = str(e)
        return (user_prompt, _fallback_script(expected_scenes, msg),
                {"source": "fallback", "reason": msg, "status": "missing_key"})

    except Exception as e:
        return (user_prompt, _fallback_script(expected_scenes, str(e)),
                {"source": "fallback", "reason": str(e), "status": "error"})
