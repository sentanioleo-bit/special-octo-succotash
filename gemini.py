import os
import json
import re
import requests

SYSTEM_PROMPT = """
You are a sharp, factual financial news anchor delivering an opening market briefing.

You will receive headlines from today's market. For EVERY story:
1. "headline": Clean, concise headline (max 8 words).
2. "script": Write exactly 2 to 3 sentences covering the specific event, numbers, percentages, dates, and what actually occurred. Explain the headline like a professional financial broadcaster.
3. "search_query": 2 to 3 visual words for stock footage (e.g., "banking vault", "trading screens", "factory assembly").

STRICT RULES:
- Never use generic filler templates (e.g., "public filings detail", "investors are tracking", "analysts watch closely").
- Stop immediately after the 2nd or 3rd factual sentence.
- You MUST output valid raw JSON with no markdown backticks.

Format:
{
  "intro": "Good morning. Here are today's top market updates.",
  "stories": [
    {
      "headline": "...",
      "script": "...",
      "search_query": "..."
    }
  ],
  "outro": "That concludes your morning briefing. Trade with discipline and manage your risk."
}
"""

def generate_broadcast_script(news_headlines: list) -> dict:
    user_prompt = "Top financial headlines to summarize:\n" + "\n".join(f"- {h}" for h in news_headlines[:15])

    # 1. Try Groq API
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            print("Connecting to Groq API...")
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
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            if res.status_code == 200:
                raw_text = res.json()["choices"][0]["message"]["content"].strip()
                data = _parse_json_safely(raw_text)
                if data and "stories" in data and len(data["stories"]) > 0:
                    print(f"Successfully generated {len(data['stories'])} stories via Groq.")
                    return data
            else:
                print(f"Groq API Error {res.status_code}: {res.text}")
        except Exception as e:
            print(f"Groq Exception: {e}")

    # 2. Try Gemini API
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            print("Connecting to Gemini API...")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\n" + user_prompt}]}
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                data = _parse_json_safely(raw_text)
                if data and "stories" in data and len(data["stories"]) > 0:
                    print(f"Successfully generated {len(data['stories'])} stories via Gemini.")
                    return data
            else:
                print(f"Gemini API Error {res.status_code}: {res.text}")
        except Exception as e:
            print(f"Gemini Exception: {e}")

    # 3. Raise error so Actions log reveals exact API failures instead of hiding behind filler
    raise RuntimeError("Both Groq and Gemini APIs failed to generate stories. Check the logs above.")

def _parse_json_safely(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned.strip())
  
