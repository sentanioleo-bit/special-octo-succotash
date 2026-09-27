import os
import random
import logging
import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

FALLBACK_QUERIES = [
    "stock market chart", "trading screen", "financial data", 
    "money trading", "stock exchange bull", "cryptocurrency trading",
    "business presentation graph", "investment analysis"
]

def fetch_motion_video(query: str, output_path: str) -> bool:
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return False

    headers = {"Authorization": api_key}
    search_url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(query)}&orientation=portrait&per_page=6"

    try:
        r = requests.get(search_url, headers=headers, timeout=12)
        data = r.json()

        videos = data.get("videos", [])
        if not videos:
            fallback = random.choice(FALLBACK_QUERIES)
            r = requests.get(f"https://api.pexels.com/videos/search?query={requests.utils.quote(fallback)}&orientation=portrait&per_page=6", headers=headers, timeout=12)
            videos = r.json().get("videos", [])

        if not videos:
            return False

        selected_video = random.choice(videos)
        video_files = selected_video.get("video_files", [])

        # Prioritize 1080x1920 or HD portrait links
        best_url = None
        for vf in video_files:
            if vf.get("width") == 1080:
                best_url = vf.get("link")
                break
        if not best_url and video_files:
            best_url = video_files[0].get("link")

        if best_url:
            resp = requests.get(best_url, stream=True, timeout=25)
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
            logger.info(f"Retrieved vertical motion video for: {query}")
            return True
    except Exception as e:
        logger.warning(f"Error fetching motion video: {e}")

    return False

def generate_fallback_card(headline: str, ticker: str, output_image_path: str):
    """Generates a professional 1080x1920 graphic card if video fetching fails."""
    width, height = 1080, 1920
    im = Image.new("RGB", (width, height), color=(10, 15, 29))
    draw = ImageDraw.Draw(im)

    # Accent Header Bar
    draw.rectangle([0, 0, width, 180], fill=(22, 33, 62))
    
    # Simple clean box for headline
    draw.rectangle([60, 400, 1020, 1000], fill=(15, 23, 42), outline=(56, 189, 248), width=3)
    
    # Ticker Badge
    draw.rectangle([60, 1050, 450, 1140], fill=(16, 185, 129))
    draw.text((80, 1070), f"⚡ {ticker.upper()}", fill=(255, 255, 255))
    draw.text((100, 480), headline, fill=(255, 255, 255))

    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    im.save(output_image_path)
    
