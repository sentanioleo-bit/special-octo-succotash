import re, requests
from pathlib import Path
from config import OPENVERSE_API, MEDIA, MEDIA_USER_AGENT
HEADERS={'User-Agent':MEDIA_USER_AGENT}

def safe(s): return re.sub(r'[^a-zA-Z0-9_-]+','_',s)[:70]

def search_openverse(query):
    r=requests.get(OPENVERSE_API, params={'q':query,'page_size':8,'mature':'false'}, headers=HEADERS, timeout=25)
    r.raise_for_status(); return r.json().get('results',[])

def download_visual(query,index):
    try:
        for item in search_openverse(query):
            url=item.get('thumbnail') or item.get('url')
            if not url: continue
            ext='.jpg'; path=MEDIA/f'{index:02d}_{safe(query)}{ext}'
            rr=requests.get(url,headers=HEADERS,timeout=30); rr.raise_for_status(); path.write_bytes(rr.content)
            return {'path':str(path),'type':'image','creator':item.get('creator',''),'license':item.get('license',''),'source':item.get('foreign_landing_url','')}
    except Exception as exc: print(f'[WARN] Openverse {query}: {exc}')
    return None
