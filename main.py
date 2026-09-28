import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"


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
        resp = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"Pexels returned {resp.status_code} for '{query}'")
            return ""
        for vid in resp.json().get("videos", []):
            files = [f for f in vid.get("video_files", []) if f.get("link")]
            good = [f for f in files if (f.get("height") or 0) >= 1280 and (f.get("width") or 0) <= 1440]
            if good:
                return good[0]["link"]
            if files:
                return files[0]["link"]
    except Exception as e:
        logger.warning(f"Pexels query '{query}' failed: {e}")
    return ""


def _fetch(query: str, target: str, key: str, fallback_query: str = "trading desk") -> Optional[str]:
    for q in (query, fallback_query):
        url = search_pexels_video(q, key)
        if url and download_file(url, target):
            return target
    return None


def collect_story_media(briefing: Dict[str, Any], out_dir: str = "work/media") -> Dict[str, Any]:
    """Returns {"hook": path|None, "stories": [path|None]*N, "outro": path|None}."""
    os.makedirs(out_dir, exist_ok=True)
    key = os.getenv("PEXELS_API_KEY", "")
    if not key:
        logger.warning("PEXELS_API_KEY not set. Videos will use a plain background.")

    hook = _fetch("stock market bull", os.path.join(out_dir, "media_hook.mp4"), key)

    stories: List[Optional[str]] = []
    for idx, story in enumerate(briefing.get("stories", []), start=1):
        query = story.get("search_query") or "stock trading chart"
        stories.append(_fetch(query, os.path.join(out_dir, f"media_story_{idx:02d}.mp4"), key))

    outro = _fetch("financial district", os.path.join(out_dir, "media_outro.mp4"), key)

    got = sum(1 for p in [hook, outro, *stories] if p)
    logger.info(f"Downloaded {got}/{len(stories) + 2} b-roll clips.")
    return {"hook": hook, "stories": stories, "outro": outro}
