import asyncio
import logging
import os
import time
from typing import Any, Dict

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


def generate_narration_audio(text: str, output_path: str, edition: str = "india") -> str:
    """Generates narration audio file using edge-tts.

    Returns the path to the generated audio file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    voice = VOICE_INDIA if edition.lower() == "india" else VOICE_GLOBAL
    _synth_with_retry(text, voice, output_path)
    return output_path
    
