import argparse
import logging
import os

from gemini import generate_briefing
from media import collect_story_media
from news_sources import fetch_market_news
from render import render_briefing_video
from tts import generate_narration_audio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline(edition: str = "india") -> str:
    logger.info(f"=== Starting Daily Market Video Engine: {edition.upper()} ===")
    os.makedirs("work", exist_ok=True)

    logger.info("Collecting news stories...")
    news_items = fetch_market_news(edition)

    logger.info("Generating 3-minute briefing script...")
    briefing = generate_briefing(news_items, edition=edition)

    logger.info("Generating narration audio clips...")
    audio_manifest = generate_narration_audio(briefing, edition=edition)

    logger.info("Collecting background video clips...")
    media = collect_story_media(briefing)

    out_file = f"work/output/{edition}_market_3min.mp4"
    logger.info(f"Rendering video to {out_file}...")
