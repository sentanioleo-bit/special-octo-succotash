import base64
from pathlib import Path
from google import genai
from config import GEMINI_API_KEY,GEMINI_TTS_MODEL,GEMINI_TTS_VOICE,WORK

def synthesize(text,out_path=None):
    if not GEMINI_API_KEY: raise RuntimeError('GEMINI_API_KEY is missing')
    out=Path(out_path or WORK/'narration.wav'); client=genai.Client(api_key=GEMINI_API_KEY)
    interaction=client.interactions.create(model=GEMINI_TTS_MODEL,input=[{'type':'user_input','content':[{'type':'text','text':text,'annotations':[{'type':'speech_metadata','style':'professional Indian digital news anchor; clear, natural, confident; moderate pace; crisp pronunciation; subtle emphasis on names and numbers'}]}]}],response_format={'type':'audio'},generation_config={'speech_config':[{'voice':GEMINI_TTS_VOICE}]})
    out.write_bytes(base64.b64decode(interaction.output_audio.data)); return out
