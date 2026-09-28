import os
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def _clean_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

def _build_exact_3min_fallback(news_items: List[Dict[str, Any]], edition: str) -> Dict[str, Any]:
    stories = []
    tickers = ["NIFTY 50", "SENSEX", "BANK NIFTY", "RELIANCE", "HDFC BANK", "TCS", "INFY", "CRUDE OIL", "GOLD", "US 10Y BOND"]
    queries = ["stock market screen", "trading desk chart", "currency exchange", "oil refinery", "wall street bull", "financial district", "corporate office", "cryptocurrency trading", "business meeting", "gold vault"]

    for i in range(10):
        item = news_items[i] if i < len(news_items) else {}
        title = item.get("title", f"Market Movement Overview {i+1}")
        words = title.split()
        headline = " ".join(words[:6]) if len(words) > 6 else title
        summary = (item.get("summary") or item.get("description") or "Trading activity continues to accelerate across major benchmark sectors.")[:160]

        # Locked ~45 words per segment
        narration = (
            f"Story {i+1}. {headline}. {summary}. "
            f"Market analysts are watching support zones closely as institutional liquidity dictates the trend. "
            f"Volume indicators highlight active consolidation going into the upcoming trading sessions."
        )

        stories.append({
            "id": i + 1,
            "headline": headline,
            "ticker": tickers[i % len(tickers)],
            "narration": narration,
            "search_query": queries[i % len(queries)]
        })

    return {
        "edition": edition,
        "yt_title": f"Top 10 Market Stories Today: Real-Time Financial Briefing",
        "yt_description": "Comprehensive daily market breakdown covering top 10 market movements.",
        "hook": "Good morning traders. Here are the top ten critical financial headlines, key index triggers, and sector movements you need to know before taking your positions today.",
        "stories": stories,
        "outro": "That concludes your daily market briefing. Maintain disciplined trade management, watch your defined risk levels, and follow for tomorrow's market opening intelligence."
    }

def generate_briefing(news_items: List[Dict[str, Any]], edition: str = "india") -> Dict[str, Any]:
    edition_label = "Indian Equity Markets (Nifty, Sensex, F&O)" if edition.lower() == "india" else "Global Financial Markets (Nasdaq, Dow, Macro)"
    
    compact_news = []
    for item in news_items[:12]:
        compact_news.append({
            "title": item.get("title", ""),
            "summary": (item.get("summary") or item.get("description") or "")[:160]
        })

    prompt = f"""
You are the executive producer of a broadcast financial news network.
Generate a structured vertical video script for {edition_label}.

AVAILABLE MARKET NEWS:
{json.dumps(compact_news, indent=2)}

STRICT TIMING & WORD COUNT REQUIREMENTS:
- Total script MUST reach 470 to 490 words to guarantee a full 180-second broadcast video at a deliberate pace.
- Hook: Exactly 28-32 words.
- Each of the 10 stories: Narration MUST be between 42 and 45 words.
- Outro: Exactly 25-28 words.

FORMAT REQUIREMENTS:
Respond in valid JSON only:
{{
  "edition": "{edition}",
  "yt_title": "Top 10 Market Stories Today: Financial Analysis",
  "yt_description": "Top 10 financial stories and sector movements.",
  "hook": "28 to 32 words spoken opening hook setting up the session.",
  "stories": [
    {{
      "id": 1,
      "headline": "Punchy Title (Max 6 words)",
      "ticker": "NIFTY +1.2%",
      "narration": "Exact 42 to 45 word spoken story script describing the news and price impact.",
      "search_query": "stock market chart"
    }}
  ],
  "outro": "25 to 28 words spoken professional closing statement."
}}
"""

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            for m in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.1-8b-instant"]:
                try:
                    res = client.chat.completions.create(
                        model=m,
                        messages=[
                            {"role": "system", "content": "You are a professional financial news producer. Output valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"}
                    )
                    content = res.choices[0].message.content
                    if content:
                        return json.loads(_clean_json(content))
                except Exception as me:
                    logger.warning(f"Groq {m} attempt failed: {me}")
        except Exception as e:
            logger.warning(f"Groq provider failed: {e}")

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            from google import genai
            g_client = genai.Client(api_key=gemini_key)
            for gm in ["gemini-2.0-flash", "gemini-3.0-flash"]:
                try:
                    res = g_client.interactions.create(model=gm, input=prompt)
                    if res and res.output_text:
                        return json.loads(_clean_json(res.output_text))
                except Exception as me:
                    logger.warning(f"Gemini {gm} attempt failed: {me}")
        except Exception as e:
            logger.warning(f"Gemini provider failed: {e}")

    logger.warning("Deploying built-in 3-minute synthesis engine...")
    return _build_exact_3min_fallback(news_items, edition)
    
