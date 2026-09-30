import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT / 'work'
MEDIA = WORK / 'media'
OUTPUT = WORK / 'output'
for p in (WORK, MEDIA, OUTPUT): p.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
GEMINI_TTS_MODEL = os.getenv('GEMINI_TTS_MODEL', 'gemini-3.8-flash-tts')
GEMINI_TTS_VOICE = os.getenv('GEMINI_TTS_VOICE', 'Kore')
VEO_MODEL = os.getenv('VEO_MODEL', 'veo-3.1-generate-preview')
MAX_AI_VIDEO_CLIPS = int(os.getenv('MAX_AI_VIDEO_CLIPS', '4'))
VIDEO_PROVIDER = os.getenv('VIDEO_PROVIDER', 'veo')  # veo | http | local | off
LOCAL_VIDEO_COMMAND = os.getenv('LOCAL_VIDEO_COMMAND', '')
LOCAL_VIDEO_TIMEOUT = int(os.getenv('LOCAL_VIDEO_TIMEOUT', '900'))

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

OPENVERSE_API = 'https://api.openverse.org/v1/images/'
MAX_STORIES = int(os.getenv('MAX_STORIES', '10'))
VIDEO_SECONDS = 180
WIDTH, HEIGHT, FPS = 1080, 1920, 30

# Used for legal/traceable media metadata.
MEDIA_USER_AGENT = 'NewsStudio/1.0 (+https://github.com/sentanioleo-bit/special-octo-succotash)'
