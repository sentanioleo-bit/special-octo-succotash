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

def generate_briefing(news_items: List[Dict[str, Any]], edition: str = "india") -> Dict[str, Any]:
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

    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    # 1. Try Groq first with automatic model discovery
    if groq_key:
        try:
            from groq import Groq
            groq_client = Groq(api_key=groq_key)
            
            # Fetch active models on this key automatically
            available_groq = [m.id for m in groq_client.models.list().data]
            logger.info(f"Available Groq models: {available_groq}")
            
            # Prioritize standard fast models
            groq_model = "llama-3.1-8b-instant"
            for cand in ["llama-3.1-8b-instant", "llama3-8b-8192", "mixtral-8x7b-32768"]:
                if cand in available_groq:
                    groq_model = cand
                    break
            else:
                if available_groq:
                    groq_model = available_groq[0]

            logger.info(f"Generating briefing via Groq ({groq_model})...")
            completion = groq_client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": "You are a financial news producer that responds strictly in valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            raw_text = completion.choices[0].message.content
            return json.loads(_clean_json(raw_text))
        except Exception as e:
            logger.warning(f"Groq generation failed: {e}. Trying Gemini...")

    # 2. Try Gemini with dynamic model listing
    if gemini_key:
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=gemini_key)
            
            # Discover supported models
            valid_gemini = []
            try:
                for m in client.models.list():
                    actions = getattr(m, "supported_actions", []) or getattr(m, "supported_generation_methods", [])
                    if "generateContent" in actions:
                        valid_gemini.append(m.name.replace("models/", ""))
            except Exception:
                pass
            
            gemini_model = valid_gemini[0] if valid_gemini else "gemini-2.0-flash"
            logger.info(f"Generating briefing via Gemini ({gemini_model})...")
            
            response = client.models.generate_content(
                model=gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            if response and response.text:
                return json.loads(_clean_json(response.text))
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")

    raise RuntimeError("Briefing generation failed across both Groq and Gemini.")
    
