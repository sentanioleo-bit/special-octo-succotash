import os, subprocess, requests, time
from pathlib import Path
from config import MEDIA, VEO_MODEL, GEMINI_API_KEY, VIDEO_PROVIDER, MAX_AI_VIDEO_CLIPS, LOCAL_VIDEO_COMMAND, LOCAL_VIDEO_TIMEOUT
from media import download_visual
from google import genai
from google.genai import types

class VideoProvider:
    name='base'
    def generate(self, prompt, index): raise NotImplementedError

class VeoProvider(VideoProvider):
    name='veo-3.1'
    def __init__(self): self.client=genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
    def generate(self,prompt,index):
        if not self.client: return None
        op=self.client.models.generate_videos(model=VEO_MODEL,prompt=prompt,config=types.GenerateVideosConfig(aspect_ratio='9:16',resolution='720p',number_of_videos=1))
        deadline=time.time()+600
        while not op.done and time.time()<deadline:
            time.sleep(8); op=self.client.operations.get(op)
        if not op.done: raise TimeoutError('Veo generation timeout')
        out=MEDIA/f'ai_{index:02d}.mp4'
        self.client.files.download(file=op.response.generated_videos[0].video,destination=str(out))
        return {'path':str(out),'type':'video','provider':self.name}

class HTTPProvider(VideoProvider):
    name='http'
    def __init__(self): self.url=os.getenv('VIDEO_PROVIDER_URL','').strip()
    def generate(self,prompt,index):
        if not self.url: return None
        r=requests.post(self.url,json={'prompt':prompt,'index':index},timeout=900); r.raise_for_status(); d=r.json()
        if d.get('path') and Path(d['path']).exists(): return {'path':d['path'],'type':'video','provider':self.name}
        if d.get('url'):
            p=MEDIA/f'provider_{index:02d}.mp4'; rr=requests.get(d['url'],timeout=900); rr.raise_for_status(); p.write_bytes(rr.content); return {'path':str(p),'type':'video','provider':self.name}
        return None

class LocalCommandProvider(VideoProvider):
    name='local'
    def generate(self,prompt,index):
        if not LOCAL_VIDEO_COMMAND: return None
        out=MEDIA/f'local_{index:02d}.mp4'
        cmd=LOCAL_VIDEO_COMMAND.format(prompt=prompt.replace('"','\\"'), output=str(out), index=index)
        subprocess.run(cmd,shell=True,check=True,timeout=LOCAL_VIDEO_TIMEOUT)
        return {'path':str(out),'type':'video','provider':self.name} if out.exists() else None

def provider():
    if VIDEO_PROVIDER=='veo': return VeoProvider()
    if VIDEO_PROVIDER=='http': return HTTPProvider()
    if VIDEO_PROVIDER=='local': return LocalCommandProvider()
    return None

def get_visual(prompt,index,ai_used):
    # AI video is deliberately capped so a daily quota cannot break the whole package.
    if ai_used < MAX_AI_VIDEO_CLIPS:
        p=provider()
        if p:
            try:
                v=p.generate(prompt,index)
                if v: return v, ai_used+1
            except Exception as exc: print(f'[WARN] {p.name} failed: {exc}')
    image=download_visual(prompt,index)
    if image: return image, ai_used
    return None, ai_used
