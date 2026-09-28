import os
import math
import logging
from typing import Dict, Any, List
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip,
    CompositeVideoClip, concatenate_videoclips, ColorClip
)

logger = logging.getLogger(__name__)

def _prepare_background(video_path: str, duration: float) -> VideoFileClip:
    if video_path and os.path.exists(video_path):
        try:
            v = VideoFileClip(video_path)
            if v.duration < duration:
                loops = math.ceil(duration / v.duration)
                v = v.loop(n=loops).subclip(0, duration)
            else:
                v = v.subclip(0, duration)
            v = v.resize(height=1920)
            x_center = (v.w - 1080) / 2
            return v.crop(x1=max(0, x_center), width=1080, height=1920)
        except Exception as e:
            logger.warning(f"Error handling video broll {video_path}: {e}")
    return ColorClip(size=(1080, 1920), color=(10, 15, 29), duration=duration)

def _build_caption_sequence(narration: str, total_duration: float) -> List[TextClip]:
    words = narration.split()
    if not words:
        return []
    
    # 4 to 5 words per subtitle card
    chunk_size = 5
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    chunk_duration = total_duration / len(chunks)
    clips = []

    for i, chunk in enumerate(chunks):
        start_time = i * chunk_duration
        clip = (
            TextClip(
                chunk.upper(),
                fontsize=46,
                color="#FFFFFF",
                font="DejaVu-Sans-Bold",
                stroke_color="black",
                stroke_width=2,
                method="caption",
                size=(920, None),
                align="center"
            )
            .set_start(start_time)
            .set_duration(chunk_duration)
            .set_position(("center", 1380))
        )
        clips.append(clip)
    return clips

def render_briefing_video(briefing: Dict[str, Any], media_assets: List[str], audio_manifest: Dict[str, Any], output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    segments = []

    # 1. Hook Segment
    hook_audio_path = audio_manifest.get("hook_audio")
    if hook_audio_path and os.path.exists(hook_audio_path):
        h_audio = AudioFileClip(hook_audio_path)
        h_dur = h_audio.duration
        h_vid = _prepare_background(media_assets[0] if media_assets else None, h_dur).set_audio(h_audio)
        
        banner = TextClip(" TODAY'S MARKET BRIEFING ", fontsize=48, color="#FACC15", font="DejaVu-Sans-Bold", bg_color="#000000").set_position(("center", 200)).set_duration(h_dur)
        captions = _build_caption_sequence(briefing.get("hook", ""), h_dur)
        segments.append(CompositeVideoClip([h_vid, banner] + captions))

    # 2. 10 Story Segments
    stories = briefing.get("stories", [])
    story_audios = audio_manifest.get("story_audios", [])

    for idx, story in enumerate(stories, start=1):
        if idx - 1 < len(story_audios):
            audio_p = story_audios[idx - 1]
            if os.path.exists(audio_p):
                s_audio = AudioFileClip(audio_p)
                s_dur = s_audio.duration
                broll_p = media_assets[idx % len(media_assets)] if media_assets else None
                s_vid = _prepare_background(broll_p, s_dur).set_audio(s_audio)

                # Segment Header: Index & Title
                headline = story.get("headline", f"Market Story {idx}")
                title_badge = TextClip(f" {idx:02d}. {headline.upper()} ", fontsize=44, color="#FACC15", font="DejaVu-Sans-Bold", bg_color="#000000").set_position(("center", 180)).set_duration(s_dur)

                # Dynamic Financial Tag
                ticker = story.get("ticker", "MARKET UPDATE")
                ticker_badge = TextClip(f" {ticker} ", fontsize=36, color="#FFFFFF", font="DejaVu-Sans-Bold", bg_color="#1E293B").set_position(("center", 250)).set_duration(s_dur)

                # Synchronized Word-Chunk Subtitles
                captions = _build_caption_sequence(story.get("narration", ""), s_dur)

                segments.append(CompositeVideoClip([s_vid, title_badge, ticker_badge] + captions))

    # 3. Outro Segment
    outro_audio_path = audio_manifest.get("outro_audio")
    if outro_audio_path and os.path.exists(outro_audio_path):
        o_audio = AudioFileClip(outro_audio_path)
        o_dur = o_audio.duration
        o_vid = _prepare_background(media_assets[-1] if media_assets else None, o_dur).set_audio(o_audio)
        out_badge = TextClip(" SUBSCRIBE FOR DAILY BRIEFINGS ", fontsize=46, color="#FACC15", font="DejaVu-Sans-Bold", bg_color="#000000").set_position(("center", 200)).set_duration(o_dur)
        captions = _build_caption_sequence(briefing.get("outro", ""), o_dur)
        segments.append(CompositeVideoClip([o_vid, out_badge] + captions))

    final_video = concatenate_videoclips(segments, method="compose")
    
    # Broadcast encoding: +faststart flag enables immediate playback without truncation
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        bitrate="2600k",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    )
    return output_path
    
