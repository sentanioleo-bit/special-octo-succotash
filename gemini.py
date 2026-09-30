import os
import json
import re

SYSTEM_PROMPT = """
You are a sharp, factual morning financial news presenter.

Structure:
- intro: Short polite morning welcome to traders (under 15 words).
- stories: Exactly 10 distinct market updates.
  - headline: Clear, concise headline.
  - script: Exactly 2 to 3 sentences covering ONLY the core facts, numbers, dates, percentage changes, or company actions.
  - search_query: A 2-to-3 word visual search term for stock video (e.g., "trading desk", "container port", "corporate office", "oil refinery").
- outro: Brief professional sign-off (under 15 words).

STRICT RULES:
1. DO NOT add generic closing lines like:
   - "Investors are tracking..."
   - "Traders are closely watching..."
   - "Market volatility impacts sector positioning..."
   - "...going into the active trading session."
2. Stop immediately after stating the 2nd or 3rd factual sentence.
3. Output strictly valid JSON matching this schema:
{
  "intro": "Good morning. Here are your top ten financial market stories for today.",
  "stories": [
    {
      "headline": "Armee Infotech Debuts on Exchanges",
      "script": "Armee Infotech is listing on the bourses today following its recent public offer. The issue saw strong subscription across retail and non-institutional categories. Initial trading begins at the opening bell.",
      "search_query": "stock exchange"
    }
  ],
  "outro": "That is your market briefing. Stay disciplined and trade safely today."
}
"""

def generate_broadcast_script(news_headlines: list) -> dict:
    user_prompt = "Top financial headlines:\n" + "\n".join(news_headlines[:15])

    # 1. Try Gemini first (most reliable for structured JSON)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config={"response_mime_type": "application/json"}
            )
            response = model.generate_content([SYSTEM_PROMPT, user_prompt])
            parsed = _parse_json_safely(response.text.strip())
            if parsed and "stories" in parsed and len(parsed["stories"]) > 0:
                print("Successfully generated script via Gemini.")
                return parsed
        except Exception as e:
            print(f"Gemini API request failed: {e}")

    # 2. Try Grok (xAI) if key is present
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
                "temperature": 0.3
            }
            res = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                raw_text = res.json()["choices"][0]["message"]["content"].strip()
                parsed = _parse_json_safely(raw_text)
                if parsed and "stories" in parsed and len(parsed["stories"]) > 0:
                    print("Successfully generated script via Grok.")
                    return parsed
        except Exception as e:
            print(f"Grok API request failed: {e}")

    # 3. Dynamic offline generator (fallback if both APIs fail or keys are missing)
    print("WARNING: API calls failed or keys missing. Falling back to dynamic summary generator.")
    return _build_fallback_script(news_headlines)

def _parse_json_safely(raw_text: str) -> dict:
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
    return json.loads(raw_text.strip())

def _build_fallback_script(headlines: list) -> dict:
    stories = []
    clean_heads = headlines[:10] if len(headlines) >= 10 else headlines + ["Market Index Update"] * (10 - len(headlines))
    for i, h in enumerate(clean_heads, start=1):
        # Clean headline text
        title = h.strip().rstrip(".")
        stories.append({
            "headline": title[:70],
            "script": f"Story {i}. {title}. Key financial details and official corporate updates were filed in exchange disclosures ahead of the bell. Review benchmark levels and stock-specific price action for updates.",
            "search_query": "stock market trading desk"
        })
    return {
        "intro": "Good morning. Here is your daily market briefing on today's top financial headlines.",
        "stories": stories,
        "outro": "That concludes today's market briefing. Have a disciplined trading session."
    }
  
