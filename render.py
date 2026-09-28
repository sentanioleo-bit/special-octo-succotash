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
