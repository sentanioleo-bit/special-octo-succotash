import re
import asyncio
import edge_tts

def normalize_text_for_anchor(text: str) -> str:
    """Expands shorthand and financial symbols so edge-tts speaks conversationally."""
    text = re.sub(r'[\?\.]{2,}', '.', text)
    text = text.replace("&amp;", "and").replace("&", "and")
    text = re.sub(r'[\(\)\[\]]', '', text)

    expansions = {
        "OFS": "Offer for Sale",
        "IPO": "I P O",
        "200 DMAs": "two hundred day moving averages",
        "200 DMA": "two hundred day moving average",
        "50 SMA": "fifty day simple moving average",
        "T+1": "T plus one",
        "SEBI's": "Sebi's",
        "SEBI": "Sebi",
        "QIB": "Qualified Institutional Buyer",
        "GMP": "Grey Market Premium",
        "cr": "crore rupees",
        "Cr": "crore rupees",
        "Rs": "rupees"
    }
    for acronym, spoken in expansions.items():
        text = re.sub(rf'\b{re.escape(acronym)}\b', spoken, text)

    # Format currencies and percentages
    text = re.sub(r'\$(\d+(\.\d+)?)', r'\1 dollars', text)
    text = re.sub(r'(\d+(\.\d+)?)%', r'\1 percent', text)
    text = re.sub(r'(\d+)\s*lakh', r'\1 lakh', text, flags=re.IGNORECASE)

    return text.strip()

async def synthesize_segment(text: str, output_path: str, voice: str = "en-IN-NeerjaNeural"):
    """
    Synthesizes speech using edge-tts.
    'en-IN-NeerjaNeural' produces a calm, polite, broadcast-quality news tone.
    """
    clean_text = normalize_text_for_anchor(text)
    communicate = edge_tts.Communicate(
        clean_text,
        voice=voice,
        rate="+5%",
        pitch="-1Hz"
    )
    await communicate.save(output_path)

def generate_audio(text: str, output_path: str, voice: str = "en-IN-NeerjaNeural"):
    asyncio.run(synthesize_segment(text, output_path, voice))
    
