import logging
import math
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

from moviepy.audio.AudioClip import AudioClip
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)
import moviepy.video.fx.all as vfx

logger = logging.getLogger(__name__)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H = 1080, 1920

CROSSFADE = 0.45
CAPTION_WORDS_PER_GROUP = 2
ENABLE_KEN_BURNS = True


def _ken_burns(clip, zoom_ratio: float = 0.045):
    duration = clip.duration

    def effect(get_frame, t):
        frame = get_frame(t)
        img = Image.fromarray(frame)
        base_size = img.size
        ratio = 1 + zoom_ratio * (t / duration if duration else 0)
        new_size = [math.ceil(base_size[0] * ratio), math.ceil(base_size[1] * ratio)]
        new_size[0] += new_size[0] % 2
        new_size[1] += new_size[1] % 2
        img = img.resize(new_size, Image.LANCZOS)
        x = (new_size[0] - base_size[0]) // 2
        y = (new_size[1] - base_size[1]) // 2
        img = img.crop((x, y, x + base_size[0], y + base_size[1]))
        return np.array(img)

    try:
        return clip.fl(effect)
    except Exception as e:
        logger.warning(f"Ken Burns effect skipped: {e}")
        return clip


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
            v = v.set_duration(duration)
            if ENABLE_KEN_BURNS:
                v = _ken_burns(v)
            return v
        except Exception as e:
            logger.warning(f"Error handling b-roll {video_path}: {e}")
    bg = ColorClip(size=(W, H), color=(10, 15, 29), duration=duration)
    return bg


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
        .fx(vfx.fadein, 0.3)
    )


def _title_card(briefing: Dict[str, Any], edition: str, duration: float = 3.0):
    bg = ColorClip(size=(W, H), color=(8, 10, 22), duration=duration)
    title_text = briefing.get("yt_title") or f"{edition.upper()} MARKET TOP 10"
    date_str = datetime.utcnow().strftime("%d %b %Y")
    title_badge = _badge(f" {title_text.upper()} ", 54, "#FACC15", "#000000", 800, duration)
    date_badge = _badge(f" {edition.upper()} EDITION | {date_str} ", 34, "#FFFFFF", "#1E293B", 960, duration)
    silent_audio = AudioClip(lambda t: 0, duration=duration, fps=44100)
    return CompositeVideoClip([bg, title_badge, date_badge], size=(W, H)).set_duration(duration).set_audio(silent_audio)


def _build_caption_sequence(narration: str, total_duration: float,
                            words: Optional[List[Dict[str, Any]]] = None,
                            chunk_size: int = CAPTION_WORDS_PER_GROUP) -> List:
    clips = []

    if words:
        for i in range(0, len(words), chunk_size):
            group = words[i:i + chunk_size]
            text = " ".join(w["word"] for w in group).strip()
            if not text:
                continue
            start = max(0.0, min(group[0]["start"], total_duration))
            end = max(start + 0.12, min(group[-1]["end"], total_duration))
            fade = min(0.06, (end - start) / 3)
            clip = (
                TextClip(
                    text.upper(),
                    fontsize=64,
                    color="#FFFFFF",
                    font=FONT,
                    stroke_color="black",
                    stroke_width=3,
                    method="caption",
                    size=(880, None),
                    align="center",
                )
                .set_start(start)
                .set_duration(end - start)
                .set_position(("center", 1420))
                .fx(vfx.fadein, fade)
                .fx(vfx.fadeout, fade)
            )
            clips.append(clip)
        if clips:
            return clips
        logger.warning("Word-level timings were empty; falling back to even caption spacing.")

    word_list = narration.split()
    if not word_list:
        return []
    chunks = [" ".join(word_list[i:i + 3]) for i in range(0, len(word_list), 3)]
    chunk_duration = total_duration / len(chunks)
    for i, chunk in enumerate(chunks):
        clip = (
            TextClip(
                chunk.upper(),
                fontsize=64,
                color="#FFFFFF",
                font=FONT,
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(880, None),
                align="center",
            )
            .set_start(i * chunk_duration)
            .set_duration(chunk_duration)
            .set_position(("center", 1420))
        )
        clips.append(clip)
    return clips


def _segment(audio_path: str, bg_path: Optional[str], overlays_fn, narration: str,
            words: Optional[List[Dict[str, Any]]] = None):
    audio = AudioFileClip(audio_path)
    dur = audio.duration
    bg = _prepare_background(bg_path, dur)
    layers = [bg] + overlays_fn(dur) + _build_caption_sequence(narration, dur, words)
    return CompositeVideoClip(layers, size=(W, H)).set_duration(dur).set_audio(audio)


def _with_crossfade(segments: List) -> List:
    out = [segments[0]]
    for clip in segments[1:]:
        out.append(clip.fx(vfx.crossfadein, CROSSFADE))
    return out


def render_briefing_video(briefing: Dict[str, Any], media: Dict[str, Any],
                          audio_manifest: Dict[str, Any], output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    edition = briefing.get("edition", "india")
    segments = [_title_card(briefing, edition)]

    hook_audio = audio_manifest.get("hook_audio")
    if hook_audio and os.path.exists(hook_audio):
        segments.append(_segment(
            hook_audio, media.get("hook"),
            lambda d: [_badge(" TODAY'S MARKET BRIEFING ", 48, "#FACC15", "#000000", 200, d)],
            briefing.get("hook", ""),
            audio_manifest.get("hook_words"),
        ))

    story_audios = audio_manifest.get("story_audios", [])
    story_words_list = audio_manifest.get("story_words", [])
    story_media = media.get("stories", [])
    for idx, story in enumerate(briefing.get("stories", []), start=1):
        if idx - 1 >= len(story_audios) or not os.path.exists(story_audios[idx - 1]):
            continue
        headline = story.get("headline", f"Market Story {idx}").upper()
        ticker = story.get("ticker", "MARKET UPDATE")
        bg = story_media[idx - 1] if idx - 1 < len(story_media) else None
        words = story_words_list[idx - 1] if idx - 1 < len(story_words_list) else None

        def overlays(d, headline=headline, ticker=ticker, idx=idx):
            return [
                _badge(f" {idx:02d}. {headline} ", 44, "#FACC15", "#000000", 180, d),
                _badge(f" {ticker} ", 36, "#FFFFFF", "#1E293B", 330, d),
            ]

        segments.append(_segment(story_audios[idx - 1], bg, overlays, story.get("narration", ""), words))

    outro_audio = audio_manifest.get("outro_audio")
    if outro_audio and os.path.exists(outro_audio):
        segments.append(_segment(
            outro_audio, media.get("outro"),
            lambda d: [_badge(" SUBSCRIBE FOR DAILY BRIEFINGS ", 46, "#FACC15", "#000000", 200, d)],
            briefing.get("outro", ""),
            audio_manifest.get("outro_words"),
        ))

    if not segments:
        raise RuntimeError("No video segments were built (missing audio files).")

    segments = _with_crossfade(segments)
    final = concatenate_videoclips(segments, method="compose", padding=-CROSSFADE)
    final = final.fx(vfx.fadein, 0.5).fx(vfx.fadeout, 0.6)
    logger.info(f"Final video duration: {final.duration:.1f}s")
    final.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="6000k",
        threads=4,
        temp_audiofile="work/temp_audio.m4a",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
    )
    return output_path
