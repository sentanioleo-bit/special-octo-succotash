import os
import json
import re

SYSTEM_PROMPT = """
You are a sharp, factual financial news anchor delivering a rapid-fire market briefing.

Structure & Rules:
- intro: Polite morning welcome to traders (maximum 15 words).
- stories: Exactly 10 distinct, major market updates.
  - Each story MUST consist of exactly 2 to 3 sentences.
  - Sentence 1: The key event or corporate headline.
  - Sentence 2: Key figures, percentages, dates, or deal sizes.
  - Sentence 3: Direct factual significance or impact.
  - search_query: A 2-to-3 word visual search term for stock footage (e.g., "trading floor", "cargo port", "oil refinery", "tech server").
- outro: Professional sign-off (maximum 15 words).

STRICT NEGATIVE CONSTRAINTS:
1. NEVER use generic filler phrases like:
   - "investors are tracking institutional order flows"
   - "technical momentum closely as market volatility impacts"
   - "sector positioning going into the active trading session"
   - "analysts are watching key levels"
2. End each story immediately after the 2nd or 3rd factual sentence.
3. Every sentence must contain distinct facts relevant only to that specific company or index.
4. Output strictly valid JSON matching this schema:
{
  "intro": "Good morning. Here are the top ten financial market headlines you need to know today.",
  "stories": [
    {
      "headline": "...",
      "script": "...",
      "search_query": "..."
    }
  ],
  "outro": "That concludes today's market briefing. Trade with discipline and watch your risk."
}
"""

def generate_broadcast_script(news_headlines: list) -> dict:
    user_prompt = "Top financial headlines:\n" + "\n".join(news_headlines[:15])

    # 1. Try Groq (Llama-3.3-70b-versatile is ultra-fast and reliable on free tier)
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            res = requests.post("[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                raw_text = res.json()["choices"][0]["message"]["content"].strip()
                data = _parse_json_safely(raw_text)
                if data and "stories" in data and len(data["stories"]) > 0:
                    print("Successfully generated news script using Groq.")
                    return data
            else:
                print(f"Groq API returned error status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"Groq API call exception: {e}")

    # 2. Try Gemini
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
            data = _parse_json_safely(response.text.strip())
            if data and "stories" in data and len(data["stories"]) > 0:
                print("Successfully generated news script using Gemini.")
                return data
        except Exception as e:
            print(f"Gemini API call exception: {e}")

    # 3. Dynamic clean fallback (Generic boilerplate is eliminated)
    print("WARNING: APIs failed. Using factual fallback script.")
    return _build_fallback_script(news_headlines)

def _parse_json_safely(raw_text: str) -> dict:
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
    return json.loads(raw_text.strip())

def _build_fallback_script(headlines: list) -> dict:
    stories = []
    clean_heads = headlines[:10] if len(headlines) >= 10 else headlines + ["Market Index Movement Reported"] * (10 - len(headlines))
    for i, h in enumerate(clean_heads, start=1):
        clean_title = h.strip().rstrip(".")
        stories.append({
            "headline": clean_title[:65],
            "script": f"Story {i}. {clean_title}. Public filings and exchange notifications detail the latest development. Further updates will be reflected in today's official exchange disclosures.",
            "search_query": "stock exchange market"
        })
    return {
        "intro": "Good morning. Here are your top ten financial market headlines for today.",
        "stories": stories,
        "outro": "That is your market briefing. Trade safely and stay disciplined."
    }
  
