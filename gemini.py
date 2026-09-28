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

