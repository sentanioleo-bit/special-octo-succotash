import os
import json
import re

SYSTEM_PROMPT = """
You are an energetic, articulate morning financial news anchor delivering a rapid-fire market briefing.

Structure & Timing:
- Target runtime: Around 3 minutes 20 seconds to 3 minutes 35 seconds.
- intro: Polite morning welcome to traders (maximum 20 words).
- stories: Exactly 10 distinct, major market updates.
  - Each story MUST be strictly between 40 and 46 words long (2 to 3 sentences).
  - Sentence 1: The key event or corporate headline.
  - Sentence 2: Concrete figures (price, percentage, support/target, or valuation).
  - Sentence 3: Direct takeaway or outlook for today's market session.
  - search_query: A 2-to-3 word visual search term for stock video (e.g., "oil refinery", "gold vault", "trading desk", "cargo ship", "bank office").
- outro: Professional sign-off reminding traders to trade with disciplined risk and follow for tomorrow's briefing (maximum 20 words).

Strict Rules:
1. Speak naturally like a TV presenter, not like reading a dry print article.
2. ABSOLUTE PROHIBITION: Never use boilerplate filler lines like "market analysts are watching support zones closely as institutional liquidity dictates the trend" or generic consolidation commentary. Every sentence must contain unique facts specific to that headline.
3. Output strictly valid JSON with NO markdown backticks or commentary:
{
  "intro": "Good morning traders, here is your daily market briefing on the top ten critical financial headlines you need to know.",
  "stories": [
    {
      "headline": "...",
      "script": "...",
      "search_query": "..."
    }
  ],
  "outro": "That concludes your daily market briefing. Maintain disciplined trade management, watch your risk, and follow for tomorrow's market opening intelligence."
}
"""

def generate_broadcast_script(news_headlines: list) -> dict:
    user_prompt = "Top financial headlines:\n" + "\n".join(news_headlines[:15])

    # 1. Try Grok (xAI) if key is present
    xai_key = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
    if xai_key:
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {xai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.4
            }
            res = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                raw_text = res.json()["choices"][0]["message"]["content"].strip()
                return _parse_json_safely(raw_text)
        except Exception as e:
            print(f"Grok API request bypassed or failed: {e}")

    # 2. Try Gemini if key is present
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([SYSTEM_PROMPT, user_prompt])
            return _parse_json_safely(response.text.strip())
        except Exception as e:
            print(f"Gemini API request bypassed or failed: {e}")

    # 3. Dynamic offline generator (guaranteed zero crash fallback)
    print("Using dynamic script synthesis fallback.")
    return _build_fallback_script(news_headlines)

def _parse_json_safely(raw_text: str) -> dict:
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
    return json.loads(raw_text.strip())

def _build_fallback_script(headlines: list) -> dict:
    stories = []
    clean_heads = headlines[:10] if len(headlines) >= 10 else headlines + ["Market Index Technical Consolidation"] * (10 - len(headlines))
    for i, h in enumerate(clean_heads, start=1):
        stories.append({
            "headline": h[:60],
            "script": f"Story {i}. {h}. Investors are tracking institutional order flows and technical momentum closely as market volatility impacts sector positioning going into the active trading session.",
            "search_query": "stock market trading desk"
        })
    return {
        "intro": "Good morning traders. Here are the top ten critical financial headlines and index triggers you need to know before taking your positions today.",
        "stories": stories,
        "outro": "That concludes your daily market briefing. Maintain disciplined trade management, watch your risk, and follow for tomorrow's market opening intelligence."
    }
  
