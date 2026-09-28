import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

GROQ_MODELS = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]


def _clean_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _valid(b: Any) -> bool:
    if not isinstance(b, dict):
        return False
    if not b.get("hook") or not b.get("outro"):
        return False
    stories = b.get("stories")
    if not isinstance(stories, list) or len(stories) < 10:
        return False
    return all(isinstance(s, dict) and s.get("narration") for s in stories[:10])


def _finalize(b: Dict[str, Any], edition: str) -> Dict[str, Any]:
    b["stories"] = b["stories"][:10]
    for i, s in enumerate(b["stories"], start=1):
        s["id"] = i
        s.setdefault("headline", f"Market Story {i}")
        s.setdefault("ticker", "MARKET UPDATE")
        s.setdefault("search_query", "stock market chart")
    b.setdefault("edition", edition)
    b.setdefault("yt_title", "Top 10 Market Stories Today")
    b.setdefault("yt_description", "Top 10 financial stories and sector movements.")
    words = sum(len(s["narration"].split()) for s in b["stories"])
    words += len(b["hook"].split()) + len(b["outro"].split())
    logger.info(f"Script ready: {words} words (~{words / 2.6:.0f}s of speech).")
    return b


def _parse(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        data = json.loads(_clean_json(text))
        return data if _valid(data) else None
    except Exception as e:
        logger.warning(f"JSON parse failed: {e}")
        return None


def _build_exact_3min_fallback(news_items: List[Dict[str, Any]], edition: str) -> Dict[str, Any]:
    stories = []
    tickers = ["NIFTY 50", "SENSEX", "BANK NIFTY", "RELIANCE", "HDFC BANK", "TCS", "INFY",
               "CRUDE OIL", "GOLD", "US 10Y BOND"]
    queries = ["stock market screen", "trading desk chart", "currency exchange", "oil refinery",
               "wall street bull", "financial district", "corporate office",
               "cryptocurrency trading", "business meeting", "gold bars"]

    for i in range(10):
        item = news_items[i] if i < len(news_items) else {}
        title = item.get("title") or f"Market Movement Overview {i + 1}"
        words = title.split()
        headline = " ".join(words[:6])
        summary = (item.get("summary") or "Trading activity continues to accelerate across major benchmark sectors.")[:160]

        narration = (
            f"Story {i + 1}. {title}. {summary}. "
            f"Market analysts are watching support zones closely as institutional liquidity dictates the trend. "
            f"Volume indicators highlight active consolidation going into the upcoming trading sessions."
        )
        stories.append({
            "id": i + 1,
            "headline": headline,
            "ticker": tickers[i % len(tickers)],
            "narration": narration,
            "search_query": queries[i % len(queries)],
        })

    return {
        "edition": edition,
        "yt_title": "Top 10 Market Stories Today: Real-Time Financial Briefing",
        "yt_description": "Comprehensive daily market breakdown covering top 10 market movements.",
        "hook": "Good morning traders. Here are the top ten critical financial headlines, key index triggers, and sector movements you need to know before taking your positions today.",
        "stories": stories,
        "outro": "That concludes your daily market briefing. Maintain disciplined trade management, watch your defined risk levels, and follow for tomorrow's market opening intelligence.",
    }


def generate_briefing(news_items: List[Dict[str, Any]], edition: str = "india") -> Dict[str, Any]:
    edition_label = (
        "Indian Equity Markets (Nifty, Sensex, F&O)"
        if edition.lower() == "india"
        else "Global Financial Markets (Nasdaq, Dow, Macro)"
    )

    compact_news = [
        {"title": it.get("title", ""), "summary": (it.get("summary") or "")[:160]}
        for it in news_items[:12]
    ]

    prompt = f"""
You are the executive producer of a broadcast financial news network.
Generate a structured vertical video script for {edition_label}.

AVAILABLE MARKET NEWS:
{json.dumps(compact_news, indent=2)}

STRICT TIMING & WORD COUNT REQUIREMENTS:
- Total script MUST reach 470 to 490 words for a full 180-second video.
- Hook: exactly 28-32 words.
- Each of the 10 stories: narration MUST be between 42 and 45 words.
- Outro: exactly 25-28 words.
- Do not invent specific prices that are not in the news; keep numbers general if unsure.

Respond with valid JSON only, in this shape:
{{
  "edition": "{edition}",
  "yt_title": "Top 10 Market Stories Today: Financial Analysis",
  "yt_description": "Top 10 financial stories and sector movements.",
  "hook": "28 to 32 word spoken opening hook.",
  "stories": [
    {{
      "id": 1,
      "headline": "Punchy Title (Max 6 words)",
      "ticker": "NIFTY +1.2%",
      "narration": "42 to 45 word spoken story script.",
      "search_query": "stock market chart"
    }}
  ],
  "outro": "25 to 28 word spoken closing statement."
}}
The "stories" array must contain exactly 10 items.
"""

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import Groq

            client = Groq(api_key=groq_key)
            for m in GROQ_MODELS:
                try:
                    res = client.chat.completions.create(
                        model=m,
                        messages=[
                            {"role": "system", "content": "You are a professional financial news producer. Output valid JSON only."},
                            {"role": "user", "content": prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.7,
                    )
                    data = _parse(res.choices[0].message.content)
                    if data:
                        logger.info(f"Script generated by Groq model {m}.")
                        return _finalize(data, edition)
                    logger.warning(f"Groq {m} returned an invalid script.")
                except Exception as me:
                    logger.warning(f"Groq {m} attempt failed: {me}")
        except Exception as e:
            logger.warning(f"Groq provider failed: {e}")

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            from google import genai
            from google.genai import types

            g_client = genai.Client(api_key=gemini_key)
            for gm in GEMINI_MODELS:
                try:
                    res = g_client.models.generate_content(
                        model=gm,
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json"),
                    )
                    data = _parse(res.text)
                    if data:
                        logger.info(f"Script generated by Gemini model {gm}.")
                        return _finalize(data, edition)
                    logger.warning(f"Gemini {gm} returned an invalid script.")
                except Exception as me:
                    logger.warning(f"Gemini {gm} attempt failed: {me}")
        except Exception as e:
            logger.warning(f"Gemini provider failed: {e}")

    logger.warning("All LLM providers failed. Using built-in fallback script.")
    return _finalize(_build_exact_3min_fallback(news_items, edition), edition)
