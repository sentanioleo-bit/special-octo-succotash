import requests
from config import TELEGRAM_BOT_TOKEN,TELEGRAM_CHAT_ID

def send_video(path,caption=''):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print('[INFO] Telegram secrets not set; skipping upload.'); return False
    url=f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo'
    with open(path,'rb') as f:
        r=requests.post(url,data={'chat_id':TELEGRAM_CHAT_ID,'caption':caption[:1000]},files={'video':f},timeout=300)
    r.raise_for_status(); return True
