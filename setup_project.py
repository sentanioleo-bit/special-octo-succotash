import os

FILES = {
    "tts.py": '''import asyncio
import logging
import os
import time
from typing import Any, Dict

import edge_tts

logger = logging.getLogger(__name__)

VOICE_INDIA = "en-IN-NeerjaNeural"
VOICE_GLOBAL = "en-US-ChristopherNeural"


async def _synth(text: str, voice: str, path: str) -> None:
    communicate = edge_tts.Communicate(text, voice, rate="-5%")
    await communicate.save(path)


def _synth_with_retry(text: str, voice: str, path: str, attempts: int = 4) -> None:
    last_err = None
    for n in range(1, attempts + 1):
        try:
            asyncio.run(_synth(text, voice, path))
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return
        except Exception as e:
            last_err = e
            logger.warning(f"TTS attempt {n} failed for {os.path.basename(path)}: {e}")
        time.sleep(2 * n)
    raise RuntimeError(f"TTS failed for {path}: {last_err}")


def generate_narration_audio(briefing: Dict[str, Any], edition: str = "india", output_dir: str = "work/audio") -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    voice = VOICE_INDIA if str(edition).lower() == "india" else VOICE_GLOBAL

    manifest: Dict[str, Any] = {
        "hook_audio": None,
        "story_audios": [],
        "outro_audio": None,
    }

    # 1. Hook
    hook_text = briefing.get("hook")
    if hook_text:
        hook_path = os.path.join(output_dir, "hook.mp3")
        logger.info("Generating Hook TTS audio...")
        _synth_with_retry(str(hook_text), voice, hook_path)
        manifest["hook_audio"] = hook_path

    # 2. Stories
    stories = briefing.get("stories", [])
    for idx, story in enumerate(stories, start=1):
        story_text = story.get("narration") or story.get("text") or str(story)
        story_path = os.path.join(output_dir, f"story_{idx:02d}.mp3")
        logger.info(f"Generating Story {idx}/{len(stories)} TTS audio...")
        _synth_with_retry(str(story_text), voice, story_path)
        manifest["story_audios"].append(story_path)

    # 3. Outro
    outro_text = briefing.get("outro")
    if outro_text:
        outro_path = os.path.join(output_dir, "outro.mp3")
        logger.info("Generating Outro TTS audio...")
        _synth_with_retry(str(outro_text), voice, outro_path)
        manifest["outro_audio"] = outro_path

    return manifest
''',

    "gemini.py": '''import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

GROQ_MODELS = ["llama-3.3-70b-versatile"]
GEMINI_MODELS = ["gemini-3.8-flash"]


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


def _finalize(b: Dict[str, Any], edition: str) -> Dict[str, Any]:
    b["stories"] = b["stories"][:10]
    for i, s in enumerate(b["stories"], start=1):
        s["id"] = i
        s.setdefault("headline", f"Market Story {i}")
        s.setdefault("ticker", "MARKET UPDATE")
        s.setdefault("search_query", "stock market chart")
    b.setdefault("edition", edition)
    b.setdefault("yt_title", "Top 10 Market Stories Today")
    b.setdefault("yt_description", "Top 10 financial stories and sector movements.")
    words = sum(len(s["narration"].split()) for s in b["stories"])
    words += len(b["hook"].split()) + len(b["outro"].split())
    logger.info(f"Script ready: {words} words (~{words / 2.6:.0f}s of speech).")
    return b


def _parse(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        data = json.loads(_clean_json(text))
        return data if _valid(data) else None
    except Exception as e:
        logger.warning(f"JSON parse failed: {e}")
        return None


def _build_exact_3min_fallback(news_items: List[Dict[str, Any]], edition: str) -> Dict[str, Any]:
    stories = []
    tickers = ["NIFTY 50", "SENSEX", "BANK NIFTY", "RELIANCE", "HDFC BANK", "TCS", "INFY",
               "CRUDE OIL", "GOLD", "US 10Y BOND"]
    queries = ["stock market screen", "trading desk chart", "currency exchange", "oil refinery",
               "wall street bull", "financial district", "corporate office",
               "cryptocurrency trading", "business meeting", "gold bars"]

    for i in range(10):
        item = news_items[i] if i < len(news_items) else {}
        title = item.get("title") or f"Market Movement Overview {i + 1}"
        words = title.split()
        headline = " ".join(words[:6])
        summary = (item.get("summary") or "Trading activity continues to accelerate across major benchmark sectors.")[:160]

        narration = (
            f"Story {i + 1}. {title}. {summary}. "
            f"Market analysts are watching support zones closely as institutional liquidity dictates the trend. "
            f"Volume indicators highlight active consolidation going into the upcoming trading sessions."
        )
        stories.append({
            "id": i + 1,
            "headline": headline,
            "ticker": tickers[i % len(tickers)],
            "narration": narration,
            "search_query": queries[i % len(queries)],
        })

    return {
        "edition": edition,
        "yt_title": "Top 10 Market Stories Today: Real-Time Financial Briefing",
        "yt_description": "Comprehensive daily market breakdown covering top 10 market movements.",
        "hook": "Good morning traders. Here are the top ten critical financial headlines, key index triggers, and sector movements you need to know before taking your positions today.",
        "stories": stories,
        "outro": "That concludes your daily market briefing. Maintain disciplined trade management, watch your defined risk levels, and follow for tomorrow's market opening intelligence.",
    }


def generate_briefing(news_items: List[Dict[str, Any]], edition: str = "india") -> Dict[str, Any]:
    edition_label = (
        "Indian Equity Markets (Nifty, Sensex, F&O)"
        if edition.lower() == "india"
        else "Global Financial Markets (Nasdaq, Dow, Macro)"
    )

    compact_news = [
        {"title": it.get("title", ""), "summary": (it.get("summary") or "")[:160]}
        for it in news_items[:12]
    ]

    prompt = f"""
You are the executive producer of a broadcast financial news network.
Generate a structured vertical video script for {edition_label}.

AVAILABLE MARKET NEWS:
{json.dumps(compact_news, indent=2)}

STRICT TIMING & WORD COUNT REQUIREMENTS:
- Total script MUST reach 470 to 490 words for a full 180-second video.
- Hook: exactly 28-32 words.
- Each of the 10 stories: narration MUST be between 42 and 45 words.
- Outro: exactly 25-28 words.
- Do not invent specific prices that are not in the news; keep numbers general if unsure.

Respond with valid JSON only, in this shape:
{{
  "edition": "{edition}",
  "yt_title": "Top 10 Market Stories Today: Financial Analysis",
  "yt_description": "Top 10 financial stories and sector movements.",
  "hook": "28 to 32 word spoken opening hook.",
  "stories": [
    {{
      "id": 1,
      "headline": "Punchy Title (Max 6 words)",
      "ticker": "NIFTY +1.2%",
      "narration": "42 to 45 word spoken story script.",
      "search_query": "stock market chart"
    }}
  ],
  "outro": "25 to 28 word spoken closing statement."
}}
The "stories" array must contain exactly 10 items.
"""

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import Groq

            client = Groq(api_key=groq_key)
            for m in GROQ_MODELS:
                try:
                    res = client.chat.completions.create(
                        model=m,
                        messages=[
                            {"role": "system", "content": "You are a professional financial news producer. Output valid JSON only."},
                            {"role": "user", "content": prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.7,
                    )
                    data = _parse(res.choices[0].message.content)
                    if data:
                        logger.info(f"Script generated by Groq model {m}.")
                        return _finalize(data, edition)
                    logger.warning(f"Groq {m} returned an invalid script.")
                except Exception as me:
                    logger.warning(f"Groq {m} attempt failed: {me}")
        except Exception as e:
            logger.warning(f"Groq provider failed: {e}")

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            from google import genai
            from google.genai import types

            g_client = genai.Client(api_key=gemini_key)
            for gm in GEMINI_MODELS:
                try:
                    res = g_client.models.generate_content(
                        model=gm,
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json"),
                    )
                    data = _parse(res.text)
                    if data:
                        logger.info(f"Script generated by Gemini model {gm}.")
                        return _finalize(data, edition)
                    logger.warning(f"Gemini {gm} returned an invalid script.")
                except Exception as me:
                    logger.warning(f"Gemini {gm} attempt failed: {me}")
        except Exception as e:
            logger.warning(f"Gemini provider failed: {e}")

    logger.warning("All LLM providers failed. Using built-in fallback script.")
    return _finalize(_build_exact_3min_fallback(news_items, edition), edition)
''',

    "media.py": '''import logging
import os
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "[https://api.pexels.com/videos/search](https://api.pexels.com/videos/search)"


def download_file(url: str, output_path: str) -> bool:
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        response = requests.get(url, stream=True, timeout=60)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return os.path.getsize(output_path) > 0
        logger.warning(f"Download failed with status: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error downloading {url}: {e}")
    return False


def search_pexels_video(query: str, api_key: str) -> str:
    if not api_key:
        return ""
    headers = {"Authorization": api_key}
    params = {"query": query, "orientation": "portrait", "size": "medium", "per_page": 5}
    try:
        res = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=15)
        if res.status_code == 200:
            data = res.json()
            videos = data.get("videos", [])
            if videos:
                for f in videos[0].get("video_files", []):
                    if f.get("quality") == "hd" or (f.get("height") or 0) >= 720:
                        return f.get("link", "")
                if videos[0].get("video_files"):
                    return videos[0]["video_files"][0].get("link", "")
    except Exception as e:
        logger.warning(f"Pexels search failed for query '{query}': {e}")
    return ""


def collect_story_media(briefing: Dict[str, Any], output_dir: str = "work/broll") -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "")

    result: Dict[str, Any] = {
        "hook": None,
        "stories": [],
        "outro": None,
    }

    # 1. Hook background
    hook_file = os.path.join(output_dir, "hook.mp4")
    url = search_pexels_video("stock market bull", pexels_key)
    if url and download_file(url, hook_file):
        result["hook"] = hook_file

    # 2. Stories background
    stories = briefing.get("stories", [])
    for idx, story in enumerate(stories, start=1):
        query = story.get("search_query") or "stock market chart"
        story_file = os.path.join(output_dir, f"story_{idx:02d}.mp4")
        url = search_pexels_video(query, pexels_key)
        if url and download_file(url, story_file):
            result["stories"].append(story_file)
        else:
            result["stories"].append(None)

    # 3. Outro background
    outro_file = os.path.join(output_dir, "outro.mp4")
    url = search_pexels_video("financial district skyline", pexels_key)
    if url and download_file(url, outro_file):
        result["outro"] = outro_file

    downloaded = sum(1 for f in [result["hook"]] + result["stories"] + [result["outro"]] if f)
    total = len(stories) + 2
    logger.info(f"Downloaded {downloaded}/{total} b-roll clips.")
    return result
''',

    "news_sources.py": '''import logging
from typing import Any, Dict, List

import feedparser

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; MarketBriefBot/1.0)"

INDIA_FEEDS = [
    "[https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms](https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms)",
    "[https://www.moneycontrol.com/rss/MCtopnews.xml](https://www.moneycontrol.com/rss/MCtopnews.xml)",
    "[https://www.livemint.com/rss/markets](https://www.livemint.com/rss/markets)",
]

GLOBAL_FEEDS = [
    "[https://feeds.content.dowjones.io/public/rss/mw_topstories](https://feeds.content.dowjones.io/public/rss/mw_topstories)",
    "[https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=markets&category=markets&format=rss](https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=markets&category=markets&format=rss)",
    "[https://feeds.bloomberg.com/markets/news.rss](https://feeds.bloomberg.com/markets/news.rss)",
]


def fetch_market_news(edition: str = "india") -> List[Dict[str, Any]]:
    feeds = INDIA_FEEDS if edition.lower() == "india" else GLOBAL_FEEDS
    items: List[Dict[str, Any]] = []
    seen = set()

    for url in feeds:
        try:
            feed = feedparser.parse(url, agent=USER_AGENT)
            for entry in feed.entries[:8]:
                title = (entry.get("title") or "").strip()
                summary = (entry.get("summary") or entry.get("description") or "").strip()
                if title and title not in seen:
                    seen.add(title)
                    items.append({"title": title, "summary": summary[:200]})
        except Exception as e:
            logger.warning(f"Failed parsing feed {url}: {e}")

    logger.info(f"Gathered {len(items)} candidate news stories for {edition.upper()}.")
    return items
''',

    "render.py": '''import logging
import os
from typing import Any, Dict, List, Optional

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

logger = logging.getLogger(__name__)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H = 1080, 1920


def _prepare_background(video_path: Optional[str], duration: float):
    if video_path and os.path.exists(video_path):
        try:
            v = VideoFileClip(video_path).without_audio()
            if v.duration < duration:
                v = v.loop(duration=duration)
            else:
                v = v.subclip(0, duration)
            scale = max(W / v.w, H / v.h)
            v = v.resize(scale)
            v = v.crop(x_center=v.w / 2, y_center=v.h / 2, width=W, height=H)
            return v.set_duration(duration)
        except Exception as e:
            logger.warning(f"Error handling b-roll {video_path}: {e}")
    return ColorClip(size=(W, H), color=(10, 15, 29), duration=duration)


def _badge(text: str, size: int, color: str, bg: str, y: int, duration: float):
    return (
        TextClip(
            text,
            fontsize=size,
            color=color,
            font=FONT,
            bg_color=bg,
            method="caption",
            size=(960, None),
            align="center",
        )
        .set_position(("center", y))
        .set_duration(duration)
    )


def _build_caption_sequence(narration: str, total_duration: float) -> List:
    words = narration.split()
    if not words:
        return []

    chunk_size = 5
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    chunk_duration = total_duration / len(chunks)
    clips = []

    for i, chunk in enumerate(chunks):
        clip = (
            TextClip(
                chunk.upper(),
                fontsize=56,
                color="#FFFFFF",
                font=FONT,
                stroke_color="black",
                stroke_width=2,
                method="caption",
                size=(920, None),
                align="center",
            )
            .set_start(i * chunk_duration)
            .set_duration(chunk_duration)
            .set_position(("center", 1380))
        )
        clips.append(clip)
    return clips


def _segment(audio_path: str, bg_path: Optional[str], overlays_fn, narration: str):
    audio = AudioFileClip(audio_path)
    dur = audio.duration
    bg = _prepare_background(bg_path, dur)
    layers = [bg] + overlays_fn(dur) + _build_caption_sequence(narration, dur)
    return CompositeVideoClip(layers, size=(W, H)).set_duration(dur).set_audio(audio)


def render_briefing_video(briefing: Dict[str, Any], media: Dict[str, Any],
                          audio_manifest: Dict[str, Any], output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    segments = []

    # 1. Hook
    hook_audio = audio_manifest.get("hook_audio")
    if hook_audio and os.path.exists(hook_audio):
        segments.append(_segment(
            hook_audio, media.get("hook"),
            lambda d: [_badge(" TODAY'S MARKET BRIEFING ", 48, "#FACC15", "#000000", 200, d)],
            briefing.get("hook", ""),
        ))

    # 2. Stories
    story_audios = audio_manifest.get("story_audios", [])
    story_media = media.get("stories", [])
    for idx, story in enumerate(briefing.get("stories", []), start=1):
        if idx - 1 >= len(story_audios) or not os.path.exists(story_audios[idx - 1]):
            continue
        headline = story.get("headline", f"Market Story {idx}").upper()
        ticker = story.get("ticker", "MARKET UPDATE")
        bg = story_media[idx - 1] if idx - 1 < len(story_media) else None

        def overlays(d, headline=headline, ticker=ticker, idx=idx):
            return [
                _badge(f" {idx:02d}. {headline} ", 44, "#FACC15", "#000000", 180, d),
                _badge(f" {ticker} ", 36, "#FFFFFF", "#1E293B", 330, d),
            ]

        segments.append(_segment(story_audios[idx - 1], bg, overlays, story.get("narration", "")))

    # 3. Outro
    outro_audio = audio_manifest.get("outro_audio")
    if outro_audio and os.path.exists(outro_audio):
        segments.append(_segment(
            outro_audio, media.get("outro"),
            lambda d: [_badge(" SUBSCRIBE FOR DAILY BRIEFINGS ", 46, "#FACC15", "#000000", 200, d)],
            briefing.get("outro", ""),
        ))

    if not segments:
        raise RuntimeError("No video segments were built (missing audio files).")

    final = concatenate_videoclips(segments, method="compose")
    logger.info(f"Final video duration: {final.durat
