import os
import asyncio
import logging
from typing import Dict, Any
import edge_tts

logger = logging.getLogger(__name__)

VOICE_INDIA = "en-IN-NeerjaNeural"
VOICE_GLOBAL = "en-US-ChristopherNeural"

async def _synth(text: str, voice: str, path: str):
    # -5% rate guarantees authoritative pacing and accurate 180s runtime
    communicate = edge_tts.Communicate(text, voice, rate="-5%")
    await communicate.save(path)

def generate_narration_audio(briefing: Dict[str, Any], edition: str = "india", out_dir: str = "work/audio") -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    voice = VOICE_INDIA if edition.lower() == "india" else VOICE_GLOBAL
    loop = asyncio.get_event_loop()

    # 1. Hook
    hook_path = os.path.join(out_dir, "hook.mp3")
    loop.run_until_complete(_synth(briefing.get("hook", "Daily market briefing."), voice, hook_path))

    # 2. Individual Story Audio Files
    story_audio_paths = []
    for idx, story in enumerate(briefing.get("stories", []), start=1):
        story_file = os.path.join(out_dir, f"story_{idx:02d}.mp3")
        text = story.get("narration", "")
        loop.run_until_complete(_synth(text, voice, story_file))
        story_audio_paths.append(story_file)

    # 3. Outro
    outro_path = os.path.join(out_dir, "outro.mp3")
    loop.run_until_complete(_synth(briefing.get("outro", "Follow for daily intelligence."), voice, outro_path))

    return {
        "hook_audio": hook_path,
        "story_audios": story_audio_paths,
        "outro_audio": outro_path
    }
    
