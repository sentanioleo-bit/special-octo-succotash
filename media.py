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
