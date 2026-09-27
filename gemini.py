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

def _build_offline_fallback(news_items: List[Dict[str, Any]], edition: str) -> Dict[str, Any]:
    """Guaranteed zero-error fallback that builds a clean briefing from collected news."""
    stories = []
    default_tickers = ["NIFTY 50", "SENSEX", "BANK NIFTY", "RELIANCE", "HDFC BANK", "TCS", "INFY", "FED RATES", "CRUDE OIL", "GOLD"]
    default_queries = ["stock market chart", "trading desk screen", "currency exchange", "oil refinery", "wall street bull", "financial district", "corporate office", "cryptocurrency trading", "business meeting", "gold vault"]

    for i in range(min(10, len(news_items))):
        item = news_items[i]
        title = item.get("title", f"Market Update Story {i+1}")
        words = title.split()
        headline = " ".join(words[:6]) if len(words) > 6 else title
        summary = (item.get("summary") or item.get("description") or "Markets continue to witness volatility amid institutional flows.")[:160]
        
        stories.append({
            "id": i + 1,
            "headline": headline,
            "ticker": default_tickers[i % len(default_tickers)],
            "narration": f"{headline}. {summary} Investors are closely tracking these key financial developments.",
            "search_query": default_queries[i % len(default_queries)]
        })

    # Fill up to 10 stories if RSS feeds had fewer than 10
    while len(stories) < 10:
        idx = len(stories)
        stories.append({
            "id": idx + 1,
            "headline": f"Key Market Development {idx+1}",
            "ticker": default_tickers[idx % len(default_tickers)],
            "narration": f"Tracking broader momentum across global and domestic indices as trading volumes sustain active institutional interest.",
            "search_query": default_queries[idx % len(default_queries)]
        })

    return {
        "edition": edition,
        "yt_title": f"Top 10 Market Stories Today: Biggest Moves & Predictions | #Shorts",
        "yt_description": "Here are today's top 10 market-moving stories. Trade prepared and follow for daily market updates.",
        "hook": "Here are the top three stories driving market momentum today. Trade prepared.",
        "stories": stories,
        "outro": "Follow for daily market intelligence before the opening bell."
    }

def generate_briefing(news_items: List[Dict[str, Any]], edition: str = "india") -> Dict[str, Any]:
    edition_name = (
        "Indian Stock Market (Nifty, Sensex, NSE/BSE)"
        if edition.lower() == "india"
        else "Global Financial Markets (Wall Street, Nasdaq, Macro)"
    )

    # 1. Compact news items to keep payloads lean
    compact_news = []
    for item in news_items[:12]:
        headline = item.get("title", "")
        summary = (item.get("summary") or item.get("description") or "")[:150]
        compact_news.append({"title": headline, "summary": summary})

    prompt = f"""
You are the senior executive producer of a premier daily financial vertical video channel.
Target audience: Traders and investors who want fast, accurate, professional analysis.

EDITION: {edition_name}
AVAILABLE RECENT NEWS:
{json.dumps(compact_news, indent=2)}

TASK:
1. Pick the 10 most impactful stories.
2. Produce a tight 3-minute narration script (~420 total words, ~145 words per minute).
3. The hook must instantly capture traders within the first 5 seconds.
4. Each story must include:
   - "headline": Short punchy title (max 7 words)
   - "ticker": Key ticker/stat (e.g., "NIFTY +1.2%", "RELIANCE EARNINGS", "FED RATES")
   - "narration": Spoken narration script (~38-42 words)
   - "search_query": A clean 2-3 word search query for financial motion video b-roll

OUTPUT SPECIFICATION: Output valid JSON only:
{{
  "edition": "{edition}",
  "yt_title": "Top 10 Market Stories Today: Biggest Moves & Predictions | #Shorts",
  "yt_description": "Here are today's top 10 market-moving stories.",
  "hook": "5-second rapid hook covering the top 3 themes of the day",
  "stories": [
    {{
      "id": 1,
      "headline": "Headline Text",
      "ticker": "NIFTY 25,100",
      "narration": "Script text spoken by voice",
      "search_query": "stock trading chart"
    }}
  ],
  "outro": "Follow for daily market intelligence before the opening bell."
}}
"""

    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    # 1. Groq generation with correct model IDs
    if groq_key:
        try:
            from groq import Groq
            groq_client = Groq(api_key=groq_key)
            
            # The active chat models verified on Groq
            for model_id in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
                try:
                    logger.info(f"Generating briefing with Groq ({model_id})...")
                    completion = groq_client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "You are a financial news producer that responds strictly in valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"}
                    )
                    raw_text = completion.choices[0].message.content
                    if raw_text:
                        return json.loads(_clean_json(raw_text))
                except Exception as m_err:
                    logger.warning(f"Groq {model_id} error: {m_err}")
        except Exception as groq_err:
            logger.warning(f"Groq failed: {groq_err}")

    # 2. Gemini fallback
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            for g_model in ["gemini-2.0-flash", "gemini-3.0-flash"]:
                try:
                    logger.info(f"Generating briefing with Gemini ({g_model})...")
                    response = client.interactions.create(
                        model=g_model,
                        input=prompt
                    )
                    if response and response.output_text:
                        return json.loads(_clean_json(response.output_text))
                except Exception as g_err:
                    logger.warning(f"Gemini {g_model} error: {g_err}")
        except Exception as gemini_err:
            logger.warning(f"Gemini failed: {gemini_err}")

    # 3. Fallback Synthesizer: constructs valid briefing directly from gathered news
    logger.warning("External AI providers failed or were rate-limited. Activating built-in news synthesizer...")
    return _build_offline_fallback(news_items, edition)
    
