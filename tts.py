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


def generate_narration_audio(briefing: Dict[str, Any], edition: str = "india", output_dir: str = "work/audio") -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    voice = VOICE_INDIA if str(edition).lower() == "india" else VOICE_GLOBAL

    manifest = {
        "hook_audio": None,
        "story_audios": [],
        "outro_audio": None,
    }

    # Hook
    hook_text = briefing.get("hook")
    if hook_text:
        hook_path = os.path.join(output_dir, "hook.mp3")
        _synth_with_retry(str(hook_text), voice, hook_path)
        manifest["hook_audio"] = hook_path

    # Stories
    for idx, story in enumerate(briefing.get("stories", []), start=1):
        story_text = story.get("narration") or story.get("text") or str(story)
        story_path = os.path.join(output_dir, f"story_{idx:02d}.mp3")
        _synth_with_retry(str(story_text), voice, story_path)
        manifest["story_audios"].append(story_path)

    # Outro
    outro_text = briefing.get("outro")
    if outro_text:
        outro_path = os.path.join(output_dir, "outro.mp3")
        _synth_with_retry(str(outro_text), voice, outro_path)
        manifest["outro_audio"] = outro_path

    return manifest
    
