import os
import requests

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
FALLBACK_QUERIES = [
    "stock trading screens",
    "financial skyscrapers",
    "modern bank office",
    "candlestick chart display",
    "business professional meeting"
]

def download_vertical_clip(query: str, output_path: str, fallback_index: int = 0) -> bool:
    """Fetches high-quality 9:16 vertical b-roll matching the specific news topic."""
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"[https://api.pexels.com/videos/search?query=](https://api.pexels.com/videos/search?query=){query}&orientation=portrait&per_page=5"
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            if videos:
                video_files = videos[0].get("video_files", [])
                # Filter for true vertical HD (1080x1920)
                vertical_files = [
                    f for f in video_files 
                    if f.get("height", 0) > f.get("width", 0) and f.get("height", 0) >= 1080
                ]
                selected_file = vertical_files[0] if vertical_files else video_files[0]
                
                with requests.get(selected_file["link"], stream=True, timeout=25) as stream:
                    with open(output_path, "wb") as f:
                        for chunk in stream.iter_content(chunk_size=1024 * 1024):
                            f.write(chunk)
                return True
    except Exception as e:
        print(f"Pexels fetch error for '{query}': {e}")

    # Fallback rotation if the query has no matching videos
    fallback_q = FALLBACK_QUERIES[fallback_index % len(FALLBACK_QUERIES)]
    print(f"Retrying with fallback keyword: {fallback_q}")
    return download_vertical_clip(fallback_q, output_path, fallback_index + 1)
    
