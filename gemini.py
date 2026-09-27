import os
import json
import logging
from typing import List, Dict, Any
from google import genai

logger = logging.getLogger(__name__)

def generate_briefing(news_items: List[Dict[str, Any]], edition: str = "india") -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from environment.")

    client = genai.Client(api_key=api_key)

    edition_name = (
        "Indian Stock Market (Nifty, Sensex, NSE/BSE)"
        if edition.lower() == "india"
        else "Global Financial Markets (Wall Street, Nasdaq, Macro)"
    )

    prompt = f"""
You are the senior executive producer of a premier daily financial vertical video channel.
Target audience: Traders and investors who want fast, accurate, professional analysis.

EDITION: {edition_name}
AVAILABLE RECENT NEWS:
{json.dumps(news_items[:30], indent=2)}

TASK:
1. Pick the 10 most impactful stories.
2. Produce a tight 3-minute narration script (~420 total words, ~145 words per minute).
3. The hook must instantly capture traders within the first 5 seconds.
4. Each story must include:
   - "headline": Short punchy title (max 7 words)
   - "ticker": Key ticker/stat (e.g., "NIFTY +1.2%", "RELIANCE EARNINGS", "FED RATES")
   - "narration": Spoken narration script (~38-42 words)
   - "search_query": A clean 2-3 word search query for financial motion video b-roll (e.g., "stock chart", "trading desk", "currency exchange", "oil refinery", "wall street bull")

OUTPUT SPECIFICATION: Output valid JSON only:
{{
  "edition": "{edition}",
  "yt_title": "Top 10 Market Stories Today: Biggest Moves & Predictions | #Shorts",
  "yt_description": "Here are today's top 10 market-moving stories. Trade prepared and follow for daily pre-market updates.",
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

    response = client.models.generate_content(
        model="gemini-3.0-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )

    try:
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Failed to parse Gemini output: {e}\n{response.text}")
        raise
        
