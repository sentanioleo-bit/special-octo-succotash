import os
import subprocess
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

def format_ass_timestamp(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs:01d}:{mins:02d}:{secs:02d}.{centis:02d}"

def generate_broadcast_ass(sub_events: list, output_ass_path: str):
    """Generates professional news styling with top headline tags and lower-third captions."""
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HeaderBanner, Arial, 42, &H0000FFFF, &H00FFFFFF, &H00000000, &H80000000, 1, 0, 0, 0, 100, 100, 1, 0, 1, 3, 2, 8, 40, 40, 190, 1
Style: BroadcastCaptions, Arial, 50, &H00FFFFFF, &H0000FFFF, &H00000000, &H90000000, 1, 0, 0, 0, 100, 100, 0, 0, 1, 3, 2, 2, 50, 50, 420, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for event in sub_events:
            start_t = format_ass_timestamp(event["start"])
            end_t = format_ass_timestamp(event["end"])
            if event.get("headline"):
                f.write(f"Dialogue: 0,{start_t},{end_t},HeaderBanner,,0,0,0,,{event['headline'].upper()}\n")
            if event.get("caption"):
                f.write(f"Dialogue: 0,{start_t},{end_t},BroadcastCaptions,,0,0,0,,{event['caption'].upper()}\n")

def compose_broadcast_video(segments_meta: list, output_mp4: str):
    """Composites 10 stories + intro/outro into a complete 1080x1920 broadcast video."""
    total_audio = sum(AudioFileClip(s["audio_path"]).duration for s in segments_meta)
    print(f"Total calculated duration: {total_audio:.1f}s ({total_audio/60:.2f} mins)")

    if total_audio > 240:
        raise ValueError(f"Duration exceeded 4-minute maximum ({total_audio:.1f}s).")

    processed_clips = []
    sub_events = []
    current_time = 0.0

    for seg in segments_meta:
        a_clip = AudioFileClip(seg["audio_path"])
        duration = a_clip.duration

        v_clip = VideoFileClip(seg["video_path"]).resize((1080, 1920))
        if v_clip.duration < duration:
            v_clip = v_clip.loop(duration=duration)
        else:
            v_clip = v_clip.subclip(0, duration)

        v_clip = v_clip.set_audio(a_clip)
        processed_clips.append(v_clip)

        sub_events.append({
            "start": current_time,
            "end": current_time + duration,
            "headline": seg.get("headline", ""),
            "caption": seg.get("script", "")
        })
        current_time += duration

    final_cut = concatenate_videoclips(processed_clips, method="compose")
    raw_video = "temp_raw_render.mp4"
    ass_path = "broadcast.ass"

    final_cut.write_videofile(
        raw_video,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        threads=4
    )

    generate_broadcast_ass(sub_events, ass_path)

    # Burn subtitles via FFmpeg
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", raw_video,
        "-vf", f"ass={ass_path}",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-c:a", "copy",
        output_mp4
    ]
    subprocess.run(ffmpeg_cmd, check=True)

    for temp_f in [raw_video, ass_path]:
        if os.path.exists(temp_f):
            os.remove(temp_f)

    print(f"Render completed: {output_mp4}")
    
