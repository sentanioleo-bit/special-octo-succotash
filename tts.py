import asyncio
import re
import os

import edge_tts


DEFAULT_VOICE = os.getenv("EDGE_TTS_VOICE", "en-IN-NeerjaNeural")
DEFAULT_RATE = os.getenv("EDGE_TTS_RATE", "-5%")
DEFAULT_PITCH = os.getenv("EDGE_TTS_PITCH", "+0Hz")


def clean_script_for_broadcast(text: str) -> str:
    """Expand common market abbreviations and make narration easier to follow."""
    text = re.sub(r"[?\.]{2,}", ".", text)
    text = text.replace("&amp;", "and").replace("& Co..", "and Company.")
    text = text.replace("&", " and ")
    text = re.sub(r"[\(\)\[\]]", "", text)

    # Longer phrases first so a shorter key does not partially consume a longer one.
    expansions = {
        "200 DMAs": "two hundred day moving averages",
        "200 DMA": "two hundred day moving average",
        "50 SMA": "fifty day simple moving average",
        "T+1": "T plus one",
        "OFS": "offer for sale",
        "IPO": "I P O",
        "QIB": "qualified institutional buyer",
        "GMP": "grey market premium",
        "SEBI's": "Sebi's",
        "SEBI": "Sebi",
        "Cr": "crore rupees",
        "cr": "crore rupees",
        "Rs": "rupees",
    }
    for word, spoken in expansions.items():
        text = re.sub(rf"\b{re.escape(word)}\b", spoken, text)

    text = re.sub(r"\$(\d+(?:\.\d+)?)", r"\1 dollars", text)
    text = re.sub(r"(\d+(?:\.\d+)?)%", r"\1 percent", text)
    text = re.sub(r"\b(\d+)\s*lakh\b", r"\1 lakh", text, flags=re.IGNORECASE)

    # Small breathing spaces after dense financial phrases and before transitions.
    text = re.sub(r"\s*([,;:])\s*", r"\1 ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def synthesize_segment(
    text: str,
    output_path: str,
    voice: str = DEFAULT_VOICE,
):
    """Generate free Edge TTS narration with a calmer, more natural pace."""
    spoken_text = clean_script_for_broadcast(text)
    communicate = edge_tts.Communicate(
        spoken_text,
        voice=voice,
        rate=DEFAULT_RATE,
        pitch=DEFAULT_PITCH,
        volume="+0%",
    )
    await communicate.save(output_path)


def generate_audio(text: str, output_path: str, voice: str = DEFAULT_VOICE):
    """Synchronous entry point used by the existing pipeline."""
    asyncio.run(synthesize_segment(text, output_path, voice))
