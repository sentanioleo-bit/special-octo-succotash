import asyncio
import logging
import os
import time
from typing import Any, Dict, List

import edge_tts

logger = logging.getLogger(__name__)

VOICE_INDIA = "en-IN-NeerjaNeural"
VOICE_GLOBAL = "en-US-ChristopherNeural"


async def _synth(text: str, voice: str, path: str) -> None:
    communicate = edge_tts.Communicate(text, voice, rate="-5%")
    await communicate.save(path)


def _synth_with_retry(text: str, voice: str, path: str, attempts: int = 4) -> None:
    last_err = None
    for n in range(1, attempts + 1):
        try:
            asyncio.run(_synth(text, voice, path))
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return
        except Exception as e:
            last_err = e
            logger.warning(f"TTS attempt {n} failed for {os.path.basename(path)}: {e}")
        time.sleep(2 * n)
    raise RuntimeError(f"TTS failed for {path}: {last_err}")


def generate_narration_audio(briefing: Any, edition: str = "india", output_dir: str = "work/audio") -> List[Dict[str, Any]]:
    """Synthesizes speech for each segment in the briefing and returns a manifest of audio files."""
    os.makedirs(output_dir, exist_ok=True)
    voice = VOICE_INDIA if str(edition).lower() == "india" else VOICE_GLOBAL

    # Normalize items if briefing is a dict containing 'segments' or 'items', or already a list
    if isinstance(briefing, dict):
        segments = briefing.get("segments") or briefing.get("items") or briefing.get("news") or [briefing]
    elif isinstance(briefing, list):
        segments = briefing
    else:
        segments = [{"text": str(briefing)}]

    manifest = []
    for idx, item in enumerate(segments):
        text = item.get("narration") or item.get("text") or item.get("script") or str(item)
        audio_file = os.path.join(output_dir, f"clip_{idx:02d}.mp3")
        
        logger.info(f"Generating TTS clip {idx + 1}/{len(segments)}: {audio_file}")
        _synth_with_retry(text, voice, audio_file)

        manifest_item = dict(item) if isinstance(item, dict) else {"text": text}
        manifest_item["audio_path"] = audio_file
        manifest.append(manifest_item)

    return manifest
    
