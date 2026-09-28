import os
import requests
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"

def download_file(url: str, output_path: str) -> bool:
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            logger.warning(f"Download failed with status: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error downloading {url}: {e}")
    return False

def search_pexels_video(query: str, api_key: str) -> str:
    if not api_key:
        return ""
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "orientation": "portrait",
        "size": "medium",
        "per_page": 5
    }
    try:
        resp = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            videos = data.get("videos", [])
            for vid in videos:
                for file_info in vid.get("video_files", []):
                    # Prefer HD vertical or standard vertical files
                    if file_info.get("height", 0) >= 1280 or file_info.get("width", 0) >= 720:
                        return file_info.get("link", "")
                if vid.get("video_files"):
                    return vid["video_files"][0].get("link", "")
    except Exception as e:
        logger.warning(f"Pexels query '{query}' failed: {e}")
    return ""

def collect_story_media(briefing: Dict[str, Any], out_dir: str = "work/media") -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "")
    downloaded_paths = []
    
    # 1. Download b-roll for Hook
    hook_query = "stock market bull"
    hook_target = os.path.join(out_dir, "media_hook.mp4")
    url = search_pexels_video(hook_query, pexels_key)
    if url and download_file(url, hook_target):
        downloaded_paths.append(hook_target)
    
    # 2. Download b-roll for each story
    for idx, story in enumerate(briefing.get("stories", []), start=1):
        query = story.get("search_query") or "stock trading chart"
        target_path = os.path.join(out_dir, f"media_story_{idx:02d}.mp4")
        
        video_url = search_pexels_video(query, pexels_key)
        if video_url and download_file(video_url, target_path):
            downloaded_paths.append(target_path)
        else:
            # Fallback to general market footage if specific query yields no results
            fallback_url = search_pexels_video("trading desk", pexels_key)
            if fallback_url and download_file(fallback_url, target_path):
                downloaded_paths.append(target_path)

    # 3. Download outro b-roll
    outro_target = os.path.join(out_dir, "media_outro.mp4")
    outro_url = search_pexels_video("financial district", pexels_key)
    if outro_url and download_file(outro_url, outro_target):
        downloaded_paths.append(outro_target)

    return downloaded_paths

# Aliases for backwards compatibility with any older caller scripts
collect_media = collect_story_media
fetch_media = collect_story_media
download_story_media = collect_story_media
