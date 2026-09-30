import os
import shutil
from gemini import generate_broadcast_script
from tts import generate_audio
from media import download_vertical_clip
from render import compose_broadcast_video

HEADLINES = [
    "Armee Infotech shares listing today check latest GMP ahead of debut",
    "Positive breakout 8 stocks cross above 200 DMA",
    "Robinhood to allow 24 hour weekend trading of US stocks",
    "Brent crude oil futures cross 104 dollars as sanctions hold",
    "Dividends and bonus issues: Last day to buy HDFC Bank, IGL",
    "Gold heads for monthly decline as US inflation data looms",
    "US dollar index hits yearly high against Euro",
    "Oil climbs further after geopolitical peace discussions stall",
    "Top stocks to watch: KPI Green, Tata Steel, NALCO",
    "Mideast crude oil shipping flows recover to 98 percent"
]

def main():
    workspace = "build_workspace"
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace, exist_ok=True)

    # Ensure work/output directory exists for GitHub Actions
    output_dir = os.path.join("work", "output")
    os.makedirs(output_dir, exist_ok=True)

    print("Step 1: Generating script via LLM or dynamic fallback...")
    script_data = generate_broadcast_script(HEADLINES)

    segments_meta = []

    # 1. Intro
    print("Step 2: Processing Intro...")
    intro_audio = os.path.join(workspace, "audio_00_intro.mp3")
    intro_video = os.path.join(workspace, "video_00_intro.mp4")
    generate_audio(script_data["intro"], intro_audio)
    download_vertical_clip("financial district morning", intro_video, 0)
    segments_meta.append({
        "headline": "TODAY'S MARKET BRIEFING",
        "script": script_data["intro"],
        "audio_path": intro_audio,
        "video_path": intro_video
    })

    # 2. Ten Stories
    for idx, story in enumerate(script_data["stories"], start=1):
        print(f"Processing Story {idx}/10: {story['headline']}...")
        audio_path = os.path.join(workspace, f"audio_{idx:02d}.mp3")
        video_path = os.path.join(workspace, f"video_{idx:02d}.mp4")

        generate_audio(story["script"], audio_path)
        download_vertical_clip(story.get("search_query", "stock market"), video_path, idx)

        segments_meta.append({
            "headline": f"STORY {idx:02d}. {story['headline']}",
            "script": story["script"],
            "audio_path": audio_path,
            "video_path": video_path
        })

    # 3. Outro
    print("Processing Outro...")
    outro_audio = os.path.join(workspace, "audio_11_outro.mp3")
    outro_video = os.path.join(workspace, "video_11_outro.mp4")
    generate_audio(script_data["outro"], outro_audio)
    download_vertical_clip("city skyline sunset", outro_video, 11)
    segments_meta.append({
        "headline": "SUBSCRIBE FOR DAILY BRIEFINGS",
        "script": script_data["outro"],
        "audio_path": outro_audio,
        "video_path": outro_video
    })

    # 4. Final Render - matching GitHub Actions path exactly
    final_output = os.path.join(output_dir, "india_market_3min.mp4")
    print(f"Step 3: Rendering video to {final_output} with subtitles...")
    compose_broadcast_video(segments_meta, final_output)
    print(f"Process complete: {final_output}")

if __name__ == "__main__":
    main()
    
