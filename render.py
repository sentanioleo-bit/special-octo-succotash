import os
import subprocess
import logging

logger = logging.getLogger(__name__)

# Small, clean subtitle styling placed at bottom-center
CLEAN_BOTTOM_SUBTITLES = (
    "FontName=DejaVu Sans,"
    "FontSize=13,"
    "PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H90000000,"
    "BorderStyle=1,"
    "Outline=1.2,"
    "Shadow=0.5,"
    "Alignment=2,"
    "MarginV=35,"
    "MarginL=25,"
    "MarginR=25"
)

def build_srt(stories: list, srt_path: str, duration_per_story: float = 17.0):
    """Creates timestamped synchronized subtitles."""
    current_time = 0.0
    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, story in enumerate(stories, start=1):
            start_s = current_time
            end_s = current_time + duration_per_story
            current_time = end_s

            start_str = f"{int(start_s//3600):02d}:{int((start_s%3600)//60):02d}:{int(start_s%60):02d},000"
            end_str = f"{int(end_s//3600):02d}:{int((end_s%3600)//60):02d}:{int(end_s%60):02d},000"

            text = story.get("narration", story.get("headline", ""))
            f.write(f"{idx}\n{start_str} --> {end_str}\n{text}\n\n")

def render_video(briefing: dict, audio_path: str, output_path: str):
    from media import fetch_motion_video, generate_fallback_card

    os.makedirs("work/clips", exist_ok=True)
    stories = briefing.get("stories", [])
    clip_paths = []

    logger.info("Preparing video visuals for each story...")
    for idx, story in enumerate(stories):
        query = story.get("search_query", "stock market trading")
        clip_path = f"work/clips/clip_{idx}.mp4"
        
        # Try getting vertical motion footage
        downloaded = fetch_motion_video(query, clip_path)
        
        if not downloaded:
            # Fallback to static card with slow zoom
            fallback_img = f"work/clips/card_{idx}.png"
            generate_fallback_card(story.get("headline", ""), story.get("ticker", ""), fallback_img)
            
            # Convert static image to 1080x1920 MP4
            subprocess.run([
                "ffmpeg", "-y", "-loop", "1", "-i", fallback_img,
                "-t", "17",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-r", "30", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast",
                clip_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Normalize motion clip to 1080x1920, 30fps, 17s
            norm_clip = f"work/clips/norm_{idx}.mp4"
            subprocess.run([
                "ffmpeg", "-y", "-i", clip_path,
                "-t", "17",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-r", "30", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-an",
                norm_clip
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.replace(norm_clip, clip_path)

        clip_paths.append(clip_path)

    # Concatenate clips
    concat_list = "work/clips/concat.txt"
    with open(concat_list, "w") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    silent_concat = "work/silent_stitched.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", silent_concat
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Subtitles
    srt_path = "work/captions.srt"
    build_srt(stories, srt_path, duration_per_story=17.0)

    # Final multiplexing: Combine video, audio narration, and clean bottom subtitles
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    abs_srt = os.path.abspath(srt_path).replace("\\", "/")
    
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", silent_concat,
        "-i", audio_path,
        "-vf", f"subtitles='{abs_srt}':force_style='{CLEAN_BOTTOM_SUBTITLES}'",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]

    logger.info("Executing final FFmpeg encode...")
    subprocess.run(ffmpeg_cmd, check=True)
    logger.info(f"Final video successfully generated: {output_path}")
    
