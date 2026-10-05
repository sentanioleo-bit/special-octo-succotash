import argparse
import os
import shutil

from gemini import generate_broadcast_script
from media import download_vertical_clip
from news_sources import fetch_market_news
from render import compose_broadcast_video
from telegram import send_video_to_telegram
from tts import generate_audio


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a market news video.")
    parser.add_argument("--edition", choices=["india", "global"], default="india")
    args = parser.parse_args()
    edition = args.edition

    workspace = os.path.join("build_workspace", edition)
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace, exist_ok=True)

    output_dir = os.path.join("work", "output")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Step 1: Fetching fresh {edition.upper()} market news...")
    news = fetch_market_news(edition=edition, max_age_hours=72, limit=20)
    if not news:
        raise RuntimeError(
            f"No recent dated stories found for {edition}. "
            "Stopping instead of generating a video from stale or hardcoded headlines."
        )

    print(f"Collected {len(news)} dated stories. Generating broadcast script...")
    script_data = generate_broadcast_script(news)
    stories = script_data.get("stories", [])
    if not stories:
        raise RuntimeError("Script generator returned no usable stories.")

    segments_meta = []

    print("Step 2: Processing intro...")
    intro_audio = os.path.join(workspace, "audio_00_intro.mp3")
    intro_video = os.path.join(workspace, "video_00_intro.mp4")
    generate_audio(script_data["intro"], intro_audio)
    if not download_vertical_clip(
        "stock market financial district trading screens", intro_video, 0
    ):
        raise RuntimeError("Could not obtain intro footage.")
    segments_meta.append({
        "headline": f"{edition.upper()} MARKET BRIEFING",
        "script": script_data["intro"],
        "audio_path": intro_audio,
        "video_path": intro_video,
    })

    for idx, story in enumerate(stories, start=1):
        headline = story["headline"]
        print(f"Processing story {idx}/{len(stories)}: {headline}")
        audio_path = os.path.join(workspace, f"audio_{idx:02d}.mp3")
        video_path = os.path.join(workspace, f"video_{idx:02d}.mp4")
        generate_audio(story["script"], audio_path)
        query = story.get("search_query") or headline
        if not download_vertical_clip(query, video_path, idx):
            raise RuntimeError(f"Could not obtain footage for story: {headline}")
        segments_meta.append({
            "headline": f"STORY {idx:02d}. {headline}",
            "script": story["script"],
            "audio_path": audio_path,
            "video_path": video_path,
        })

    print("Processing outro...")
    outro_audio = os.path.join(workspace, "audio_outro.mp3")
    outro_video = os.path.join(workspace, "video_outro.mp4")
    generate_audio(script_data["outro"], outro_audio)
    if not download_vertical_clip(
        "modern city skyline financial district", outro_video, len(stories) + 1
    ):
        raise RuntimeError("Could not obtain outro footage.")
    segments_meta.append({
        "headline": "FOLLOW FOR DAILY MARKET BRIEFINGS",
        "script": script_data["outro"],
        "audio_path": outro_audio,
        "video_path": outro_video,
    })

    final_output = os.path.join(output_dir, f"{edition}_market_3min.mp4")
    print(f"Step 3: Rendering video to {final_output}...")
    compose_broadcast_video(segments_meta, final_output)
    if not os.path.isfile(final_output) or os.path.getsize(final_output) == 0:
        raise RuntimeError("Render did not produce a non-empty MP4.")

    print(f"Video ready: {final_output}")
    delivered = send_video_to_telegram(final_output, script_data, edition=edition)
    if delivered:
        print("Telegram video upload succeeded.")
    else:
        print("Telegram direct upload skipped or failed; workflow release link can still be sent.")


if __name__ == "__main__":
    main()
