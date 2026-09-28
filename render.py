import logging
import os
from typing import Any, Dict, List, Optional

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

logger = logging.getLogger(__name__)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H = 1080, 1920


def _prepare_background(video_path: Optional[str], duration: float):
    if video_path and os.path.exists(video_path):
        try:
            v = VideoFileClip(video_path).without_audio()
            if v.duration < duration:
                v = v.loop(duration=duration)
            else:
                v = v.subclip(0, duration)
            scale = max(W / v.w, H / v.h)
            v = v.resize(scale)
            v = v.crop(x_center=v.w / 2, y_center=v.h / 2, width=W, height=H)
            return v.set_duration(duration)
        except Exception as e:
            logger.warning(f"Error handling b-roll {video_path}: {e}")
    return ColorClip(size=(W, H), color=(10, 15, 29), duration=duration)


def _badge(text: str, size: int, color: str, bg: str, y: int, duration: float):
    return (
        TextClip(
            text,
            fontsize=size,
            color=color,
            font=FONT,
            bg_color=bg,
            method="caption",
            size=(960, None),
            align="center",
        )
        .set_position(("center", y))
        .set_duration(duration)
    )


def _build_caption_sequence(narration: str, total_duration: float) -> List:
    words = narration.split()
    if not words:
        return []

    chunk_size = 5
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    chunk_duration = total_duration / len(chunks)
    clips = []

    for i, chunk in enumerate(chunks):
        clip = (
            TextClip(
                chunk.upper(),
                fontsize=56,
                color="#FFFFFF",
                font=FONT,
                stroke_color="black",
                stroke_width=2,
                method="caption",
                size=(920, None),
                align="center",
            )
            .set_start(i * chunk_duration)
            .set_duration(chunk_duration)
            .set_position(("center", 1380))
        )
        clips.append(clip)
    return clips


def _segment(audio_path: str, bg_path: Optional[str], overlays_fn, narration: str):
    audio = AudioFileClip(audio_path)
    dur = audio.duration
    bg = _prepare_background(bg_path, dur)
    layers = [bg] + overlays_fn(dur) + _build_caption_sequence(narration, dur)
    return CompositeVideoClip(layers, size=(W, H)).set_duration(dur).set_audio(audio)


def render_briefing_video(briefing: Dict[str, Any], media: Dict[str, Any],
                          audio_manifest: Dict[str, Any], output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    segments = []

    hook_audio = audio_manifest.get("hook_audio")
    if hook_audio and os.path.exists(hook_audio):
        segments.append(_segment(
            hook_audio, media.get("hook"),
            lambda d: [_badge(" TODAY'S MARKET BRIEFING ", 48, "#FACC15", "#000000", 200, d)],
            briefing.get("hook", ""),
        ))

    story_audios = audio_manifest.get("story_audios", [])
    story_media = media.get("stories", [])
    for idx, story in enumerate(briefing.get("stories", []), start=1):
        if idx - 1 >= len(story_audios) or not os.path.exists(story_audios[idx - 1]):
            continue
        headline = story.get("headline", f"Market Story {idx}").upper()
        ticker = story.get("ticker", "MARKET UPDATE")
        bg = story_media[idx - 1] if idx - 1 < len(story_media) else None

        def overlays(d, headline=headline, ticker=ticker, idx=idx):
            return [
                _badge(f" {idx:02d}. {headline} ", 44, "#FACC15", "#000000", 180, d),
                _badge(f" {ticker} ", 36, "#FFFFFF", "#1E293B", 330, d),
            ]

        segments.append(_segment(story_audios[idx - 1], bg, overlays, story.get("narration", "")))

    outro_audio = audio_manifest.get("outro_audio")
    if outro_audio and os.path.exists(outro_audio):
        segments.append(_segment(
            outro_audio, media.get("outro"),
            lambda d: [_badge(" SUBSCRIBE FOR DAILY BRIEFINGS ", 46, "#FACC15", "#000000", 200, d)],
            briefing.get("outro", ""),
        ))

    if not segments:
        raise RuntimeError("No video segments were built (missing audio files).")

    final = concatenate_videoclips(segments, method="compose")
    logger.info(f"Final video duration: {final.duration:.1f}s")
    final.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        bitrate="2600k",
        threads=4,
        temp_audiofile="work/temp_audio.m4a",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
    )
    return output_path
