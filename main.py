import argparse
import os
import shutil

from moviepy.editor import AudioFileClip

from gemini import generate_broadcast_script
from media import download_vertical_clip
from news_sources import fetch_market_news
from render import compose_broadcast_video
from telegram import send_message_to_telegram, send_video_to_telegram
from youtube_metadata import build_youtube_metadata, write_youtube_metadata
from tts import generate_audio

MAX_STORIES = 8
MAX_AUDIO_SECONDS = 230  # Keep safely below render.py's four-minute hard limit.


def _audio_duration(path: str) -> float:
    clip = AudioFileClip(path)
    try:
        return float(clip.duration or 0)
    finally:
        clip.close()


def _fit_duration(segments: list[dict]) -> list[dict]:
    """Drop the least-recent story segments if narration would exceed the render limit."""
    kept = list(segments)

    def total_seconds() -> float:
        return sum(_audio_duration(segment["audio_path"]) for segment in kept)

    duration = total_seconds()
    while duration > MAX_AUDIO_SECONDS:
        story_indexes = [
            i for i, segment in enumerate(kept)
            if segment.get("kind") == "story"
        ]
        if not story_indexes:
            raise RuntimeError(
                f"Intro/outro narration alone exceeds the video duration limit "
                f"({duration:.1f}s). Please shorten the intro/outro scripts."
            )
        removed = kept.pop(story_indexes[-1])
        print(
            f"Duration safety: omitting story to fit the 4-minute render limit: "
            f"{removed['headline']}"
        )
        duration = total_seconds()

    print(f"Final narration duration: {duration:.1f}s ({duration / 60:.2f} minutes)")
    return kept


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
    news = fetch_market_news(edition=edition, max_age_hours=168, limit=20)
    if not news:
        raise RuntimeError(
            f"No recent dated stories found for {edition}. "
            "Stopping instead of generating a video from stale or hardcoded headlines."
        )

    print(f"Collected {len(news)} dated stories. Generating a concise broadcast script...")
    script_data = generate_broadcast_script(news[:MAX_STORIES])
    stories = script_data.get("stories", [])[:MAX_STORIES]
    if not stories:
        raise RuntimeError("Script generator returned no usable stories.")
    script_data["stories"] = stories
    print(f"Using {len(stories)} stories to keep the video within its duration target.")

    metadata = build_youtube_metadata(edition, stories)
    script_data.update(metadata)
    metadata_path = os.path.join(output_dir, f"{edition}_youtube_metadata.txt")
    write_youtube_metadata(metadata, metadata_path)
    print(f"YouTube title/tags/description saved to {metadata_path}")

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
        "kind": "intro",
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
            "kind": "story",
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
        "kind": "outro",
        "headline": "FOLLOW FOR DAILY MARKET BRIEFINGS",
        "script": script_data["outro"],
        "audio_path": outro_audio,
        "video_path": outro_video,
    })

    segments_meta = _fit_duration(segments_meta)

    final_output = os.path.join(output_dir, f"{edition}_market_3min.mp4")
    print(f"Step 3: Rendering video to {final_output}...")
    compose_broadcast_video(segments_meta, final_output)
    if not os.path.isfile(final_output) or os.path.getsize(final_output) == 0:
        raise RuntimeError("Render did not produce a non-empty MP4.")

    print(f"Video ready: {final_output}")
    delivered = send_video_to_telegram(final_output, script_data, edition=edition)
    metadata_sent = send_message_to_telegram(metadata, edition=edition)
    if metadata_sent:
        print("Customized YouTube title, description, and tags sent to Telegram.")
    if delivered:
        print("Telegram video upload succeeded.")
    else:
        print("Telegram direct upload skipped or failed; workflow release link can still be sent.")


if __name__ == "__main__":
    main()
