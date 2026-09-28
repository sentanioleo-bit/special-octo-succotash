import os
import argparse
import logging
from news_sources import fetch_market_news
from gemini import generate_briefing
from tts import generate_narration_audio
from media import collect_story_media
from render import render_briefing_video

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def run_pipeline(edition: str = "india"):
    logger.info(f"=== Starting Daily Market Video Engine: {edition.upper()} ===")
    
    # 1. Fetch News
    logger.info("Collecting news stories...")
    news_items = fetch_market_news(edition)
    
    # 2. Generate 3-Minute Script
    logger.info("Generating 3-minute briefing script...")
    briefing = generate_briefing(news_items, edition=edition)
    
    # 3. Synchronized Story Audio
    logger.info("Generating narration audio clips...")
    audio_manifest = generate_narration_audio(briefing, edition=edition)
    
    # 4. Collect Media B-Roll
    logger.info("Collecting background video clips...")
    media_assets = collect_story_media(briefing)
    
    # 5. Render Video
    out_file = f"work/output/{edition}_market_3min.mp4"
    logger.info(f"Rendering synchronized video to {out_file}...")
    render_briefing_video(briefing, media_assets, audio_manifest, out_file)
    logger.info(f"=== {edition.upper()} Video Render Complete: {out_file} ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--edition", default="india", choices=["india", "global"])
    args = parser.parse_args()
    run_pipeline(args.edition)
    
