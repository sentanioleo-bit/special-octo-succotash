import os
import requests

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# 12 diverse vertical stock video assets that require zero API key
PUBLIC_STOCK_VIDEOS = [
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WhatCarCanYouGetForAGrand.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WhatCarCanYouGetForAGrand.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4)",
    "[https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4](https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4)"
]

def download_vertical_clip(query: str, output_path: str, fallback_idx: int = 0) -> bool:
    """Downloads vertical b-roll footage. Uses Pexels if a key exists; otherwise uses public stock pools."""
    if PEXELS_API_KEY:
        try:
            headers = {"Authorization": PEXELS_API_KEY}
            url = f"[https://api.pexels.com/videos/search?query=](https://api.pexels.com/videos/search?query=){query}&orientation=portrait&per_page=5"
            response = requests.get(url, headers=headers, timeout=12)
            if response.status_code == 200:
                data = response.json()
                videos = data.get("videos", [])
                if videos:
                    video_files = videos[0].get("video_files", [])
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
            print(f"Pexels fetch error: {e}")

    # Zero-key fallback: Cycle through distinct high-quality stock videos
    chosen_url = PUBLIC_STOCK_VIDEOS[fallback_idx % len(PUBLIC_STOCK_VIDEOS)]
    try:
        with requests.get(chosen_url, stream=True, timeout=25) as r:
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
        return True
    except Exception as err:
        print(f"Fallback clip download failed: {err}")
        return False
        
