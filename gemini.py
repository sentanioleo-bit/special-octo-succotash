import os
import json
import re
import requests

# Current production model IDs.
# Groq retired llama-3.3-70b-versatile on 2026-08-16.
# Gemini 1.5 Flash is no longer available on the current API.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


SYSTEM_PROMPT = """
You are a sharp, factual financial news anchor delivering an opening market briefing.

You will receive headlines from today's market. For EVERY story:
1. "headline": Clean, concise headline (max 8 words).
2. "script": Exactly 2 to 3 short factual sentences covering the specific event,
   numbers, percentages, dates, and what actually occurred.
3. "search_query": 2 to 3 visual words for stock footage.

STRICT RULES:
- Never use generic filler templates.
- Stop immediately after the 2nd or 3rd factual sentence.
- Never invent facts.
- Never give investment advice.
- Do not turn a headline into a claim that is not supported by the supplied text.
- Return valid JSON only. No markdown fences.

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
  "outro": "That concludes today's market briefing."
}
"""


def _parse_json_safely(raw_text: str) -> dict:
    cleaned = (raw_text or "").strip()

    # Remove markdown code fences if a provider ignores JSON-only instruction.
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Recover the first JSON object from accidental surrounding text.
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise ValueError(
                "LLM returned invalid JSON:\n" + cleaned[:3000]
            )
        return json.loads(match.group(0))


def _validate(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a JSON object.")

    stories = data.get("stories")
    if not isinstance(stories, list) or not stories:
        raise ValueError("LLM response contains no stories.")

    cleaned = []
    for story in stories:
        if not isinstance(story, dict):
            continue

        headline = str(story.get("headline", "")).strip()
        script = str(story.get("script", "")).strip()
        search_query = str(story.get("search_query", "stock market")).strip()

        if not headline or not script:
            continue

        cleaned.append({
            "headline": headline[:120],
            "script": script,
            "search_query": search_query[:120],
        })

    if not cleaned:
        raise ValueError("LLM returned no usable stories.")

    data["stories"] = cleaned
    data.setdefault(
        "intro",
        "Good morning. Here are today's top market updates."
    )
    data.setdefault(
        "outro",
        "That concludes today's market briefing."
    )
    return data


def _build_user_prompt(news_headlines: list) -> str:
    lines = []

    for item in news_headlines[:15]:
        if isinstance(item, dict):
            title = str(item.get("title", "")).strip()
            summary = str(item.get("summary", "")).strip()
            if summary:
                lines.append(f"- {title} — {summary}")
            else:
                lines.append(f"- {title}")
        else:
            lines.append(f"- {item}")

    return "Top financial headlines to summarize:\n" + "\n".join(lines)


def _generate_with_groq(user_prompt: str) -> dict:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    print(f"Connecting to Groq API using model: {GROQ_MODEL}")

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 4000,
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=90,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Groq API Error {response.status_code}: {response.text[:2000]}"
        )

    body = response.json()

    try:
        raw_text = body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError) as exc:
        raise RuntimeError(
            "Unexpected Groq response: " + json.dumps(body)[:3000]
        ) from exc

    return _validate(_parse_json_safely(raw_text))


def _generate_with_gemini(user_prompt: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    print(f"Connecting to Gemini API using model: {GEMINI_MODEL}")

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": SYSTEM_PROMPT
                        + "\n\n"
                        + user_prompt
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    response = requests.post(
        url,
        params={"key": api_key},
        json=payload,
        timeout=90,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini API Error {response.status_code}: "
            f"{response.text[:3000]}"
        )

    body = response.json()

    try:
        raw_text = (
            body["candidates"][0]["content"]["parts"][0]["text"].strip()
        )
    except (KeyError, IndexError, AttributeError) as exc:
        raise RuntimeError(
            "Unexpected Gemini response: " + json.dumps(body)[:3000]
        ) from exc

    return _validate(_parse_json_safely(raw_text))


def generate_broadcast_script(news_headlines: list) -> dict:
    """
    Primary: Groq GPT-OSS 120B.
    Fallback: Gemini 3.8 Flash.

    This preserves the existing main.py interface, so no other caller
    changes are required.
    """
    user_prompt = _build_user_prompt(news_headlines)

    groq_error = None
    gemini_error = None

    # 1. Groq
    if os.getenv("GROQ_API_KEY"):
        try:
            result = _generate_with_groq(user_prompt)
            print(
                f"Successfully generated {len(result['stories'])} "
                "stories via Groq."
            )
            return result
        except Exception as exc:
            groq_error = str(exc)
            print(f"Groq failed: {groq_error}")
    else:
        groq_error = "GROQ_API_KEY is not configured."
        print(groq_error)

    # 2. Gemini
    if os.getenv("GEMINI_API_KEY"):
        try:
            result = _generate_with_gemini(user_prompt)
            print(
                f"Successfully generated {len(result['stories'])} "
                "stories via Gemini."
            )
            return result
        except Exception as exc:
            gemini_error = str(exc)
            print(f"Gemini failed: {gemini_error}")
    else:
        gemini_error = "GEMINI_API_KEY is not configured."
        print(gemini_error)

    raise RuntimeError(
        "Both Groq and Gemini APIs failed.\n\n"
        f"GROQ: {groq_error}\n\n"
        f"GEMINI: {gemini_error}"
    )
