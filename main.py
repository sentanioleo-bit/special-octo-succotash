import os
import argparse
import json
import logging

from news_sources import fetch_market_news
from gemini import generate_briefing
from tts import synthesize
from render import render_video
from telegram import send_video_to_telegram

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def run_pipeline(edition: str = "india"):
    os.makedirs("work/output", exist_ok=True)
    logger.info(f"=== Starting Daily Market Video Engine: {edition.upper()} ===")

    # 1. Collect fresh 24h market feeds
    logger.info("Collecting 24h market stories...")
    items = fetch_market_news(edition=edition, hours_fresh=24)
    if not items:
        logger.warning("No items within 24h window; checking 48h...")
        items = fetch_market_news(edition=edition, hours_fresh=48)

    logger.info(f"Gathered {len(items)} fresh candidate stories.")

    # 2. Editorial Selection & Scriptwriting
    briefing = generate_briefing(items, edition=edition)
    with open(f"work/briefing_{edition}.json", "w") as f:
        json.dump(briefing, f, indent=2)

    # 3. Audio Narration
    audio_path = f"work/narration_{edition}.mp3"
    full_script = briefing.get("hook", "") + " "
    for s in briefing.get("stories", []):
        full_script += s.get("narration", "") + " "
    full_script += briefing.get("outro", "")

    synthesize(full_script, audio_path)

    # 4. Render 1080x1920 MP4
    video_output = f"work/output/{edition}_market_3min.mp4"
    render_video(briefing=briefing, audio_path=audio_path, output_path=video_output)

    # 5. Telegram Delivery
    send_video_to_telegram(video_path=video_output, briefing_data=briefing, edition=edition)

    logger.info(f"=== {edition.upper()} Video Render and Delivery Complete! ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--edition", type=str, default="india", choices=["india", "global"])
    args = parser.parse_args()

    run_pipeline(edition=args.edition)
    
