import os
import textwrap
import urllib.parse
import subprocess

import requests
from PIL import Image, ImageDraw, ImageFont

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
_USED_PEXELS_IDS: set[str] = set()


def _font(size: int, bold: bool = False):
    candidates = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    )
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _make_branded_fallback(query: str, output_path: str) -> bool:
    """Create a clean branded motion-card fallback instead of unrelated demo footage."""
    try:
        width, height = 1080, 1920
        image = Image.new("RGB", (width, height))
        pixels = image.load()
        for y in range(height):
            t = y / max(height - 1, 1)
            color = (int(8 + 5 * t), int(16 + 9 * t), int(32 + 18 * t))
            for x in range(width):
                pixels[x, y] = color

        draw = ImageDraw.Draw(image)
        accent = (0, 170, 255)
        draw.rounded_rectangle((64, 90, 1016, 178), radius=28, fill=(13, 33, 57), outline=accent, width=3)
        draw.text((94, 112), "NEWS STUDIO  /  MARKET BRIEFING", font=_font(31, True), fill=(240, 248, 255))
        draw.line((70, 370, 1010, 370), fill=accent, width=5)
        draw.text((72, 420), "MARKET UPDATE", font=_font(36, True), fill=accent)
        cleaned = " ".join((query or "Financial markets").split()).strip()
        lines = textwrap.wrap(cleaned[:150], width=23) or ["Financial markets"]
        y = 510
        for line in lines[:5]:
            draw.text((72, y), line, font=_font(62, True), fill=(255, 255, 255), stroke_width=1)
            y += 88
        draw.rounded_rectangle((72, 1480, 1008, 1600), radius=22, fill=(12, 29, 49), outline=(40, 82, 120), width=2)
        draw.text((105, 1518), "LATEST DEVELOPMENTS  •  MARKET NEWS", font=_font(25, True), fill=(210, 230, 248))
        draw.text((72, 1695), "News Studio", font=_font(32, True), fill=(160, 190, 220))
        poster = os.path.splitext(output_path)[0] + "_poster.jpg"
        image.save(poster, quality=92)
        subprocess.run(
            ["ffmpeg", "-y", "-loop", "1", "-i", poster, "-t", "8",
             "-vf", "scale=1080:1920,format=yuv420p", "-r", "30",
             "-an", "-c:v", "libx264", "-preset", "ultrafast", output_path],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        os.remove(poster)
        return os.path.isfile(output_path) and os.path.getsize(output_path) > 0
    except Exception as err:
        print(f"Branded fallback creation failed: {err}")
        return False


def download_vertical_clip(query: str, output_path: str, fallback_idx: int = 0) -> bool:
    """Download relevant portrait footage from Pexels or create a branded fallback."""
    clean_query = " ".join(str(query).split()).strip() or "financial markets"
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if PEXELS_API_KEY:
        try:
            encoded_query = urllib.parse.quote(clean_query)
            url = (
                "https://api.pexels.com/videos/search?"
                f"query={encoded_query}&orientation=portrait&per_page=15"
            )
            response = requests.get(
                url, headers={"Authorization": PEXELS_API_KEY}, timeout=15
            )
            response.raise_for_status()
            videos = response.json().get("videos", [])
            # Try multiple results and skip clips already used in this run.
            videos.sort(key=lambda v: (v.get("width", 0) < v.get("height", 0),
                                       v.get("duration", 0) >= 8), reverse=True)
            for video in videos:
                video_id = str(video.get("id", ""))
                if video_id and video_id in _USED_PEXELS_IDS:
                    continue
                files = video.get("video_files", [])
                files.sort(
                    key=lambda f: (
                        f.get("height", 0) > f.get("width", 0),
                        f.get("height", 0) >= 1080,
                        f.get("width", 0) * f.get("height", 0),
                    ),
                    reverse=True,
                )
                for video_file in files:
                    link = (video_file.get("link") or "").strip()
                    if not link.startswith("https://"):
                        continue
                    try:
                        with requests.get(link, stream=True, timeout=30) as stream:
                            stream.raise_for_status()
                            with open(output_path, "wb") as out:
                                for chunk in stream.iter_content(chunk_size=1024 * 1024):
                                    if chunk:
                                        out.write(chunk)
                        if os.path.getsize(output_path) > 0:
                            if video_id:
                                _USED_PEXELS_IDS.add(video_id)
                            print(f"Downloaded relevant Pexels footage for: {clean_query}")
                            return True
                    except requests.RequestException:
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        continue
        except Exception as err:
            print(f"Pexels fetch error for '{clean_query}': {err}")

    print(f"Using branded fallback visual for: {clean_query}")
    return _make_branded_fallback(clean_query, output_path)
