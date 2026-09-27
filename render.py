import subprocess, json, math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from config import WIDTH,HEIGHT,FPS,WORK,OUTPUT

def run(cmd):
    print('$',' '.join(map(str,cmd))); subprocess.run(cmd,check=True)

def font(size,bold=False):
    p='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(p,size) if Path(p).exists() else ImageFont.load_default()

def fallback_card(path,category,headline,overlay=''):
    img=Image.new('RGB',(WIDTH,HEIGHT),(7,11,18)); d=ImageDraw.Draw(img)
    d.rectangle((0,0,WIDTH,22),fill=(25,125,220)); d.text((70,110),category.upper(),font=font(36,True),fill=(100,190,255))
    words=headline.split(); lines=[]; line=''
    for w in words:
        test=(line+' '+w).strip()
        if d.textbbox((0,0),test,font=font(70,True))[2]>WIDTH-140: lines.append(line); line=w
        else: line=test
    if line: lines.append(line)
    y=690
    for ln in lines[:5]: d.text((70,y),ln,font=font(70,True),fill='white'); y+=92
    if overlay: d.text((70,HEIGHT-300),overlay,font=font(38,True),fill=(210,220,235))
    d.text((70,HEIGHT-120),'DAILY NEWS • ORIGINAL BRIEFING',font=font(30),fill=(140,150,165)); img.save(path,quality=95)

def srt_time(x):
    ms=int(round((x-int(x))*1000)); t=int(x); h,t=divmod(t,3600); m,s=divmod(t,60); return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def build_srt(briefing):
    texts=[briefing['hook']]+[s['narration'] for s in briefing['stories']]+[briefing['ending']]
    total=sum(max(1,len(x.split())) for x in texts); t=0; idx=1; out=[]
    for text in texts:
        dur=180*len(text.split())/total; words=text.split(); chunks=[words[i:i+7] for i in range(0,len(words),7)]; step=dur/max(1,len(chunks))
        for j,c in enumerate(chunks):
            a=t+j*step; b=min(t+(j+1)*step,180); out.append(f'{idx}\n{srt_time(a)} --> {srt_time(b)}\n{" ".join(c)}\n'); idx+=1
        t+=dur
    p=WORK/'captions.srt'; p.write_text('\n'.join(out),encoding='utf-8'); return p

def make_clip(asset,duration,index):
    p=Path(asset['path']); out=WORK/f'shot_{index:03d}.mp4'
    if asset.get('type')=='video':
        vf=f'scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},format=yuv420p'
        run(['ffmpeg','-y','-stream_loop','-1','-i',str(p),'-t',str(duration),'-vf',vf,'-an','-r',str(FPS),'-c:v','libx264','-preset','fast','-crf','20',str(out)])
    else:
        vf=(f"scale={WIDTH*2}:{HEIGHT*2}:force_original_aspect_ratio=increase,crop={WIDTH*2}:{HEIGHT*2},"
             f"zoompan=z='min(zoom+0.0008,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p")
        run(['ffmpeg','-y','-loop','1','-i',str(p),'-t',str(duration),'-vf',vf,'-an','-r',str(FPS),'-c:v','libx264','-preset','fast','-crf','20',str(out)])
    return out

def render_video(briefing, narration_wav, story_assets):
    shots=[]; idx=0
    for si,story in enumerate(briefing['stories'],1):
        assets=story_assets.get(si,[])
        # Ensure exactly ~17-18 sec per story. Use up to 3 shots.
        for asset in assets[:3]:
            duration=float(asset.get('duration',6))
            shots.append(make_clip(asset,duration,idx)); idx+=1
    if not shots:
        raise RuntimeError('No visual shots available')
    lst=WORK/'concat.txt'
    with lst.open('w') as f:
        for p in shots: f.write(f"file '{p.resolve()}'\n")
    silent=WORK/'silent.mp4'; srt=build_srt(briefing); output=OUTPUT/'daily_news_3min.mp4'
    run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(lst),'-t','180','-an','-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p',str(silent)])
    subtitle_style="FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=100"
    run(['ffmpeg','-y','-i',str(silent),'-i',str(narration_wav),'-t','180','-vf',f"subtitles={srt}:force_style='{subtitle_style}'",'-c:v','libx264','-preset','medium','-crf','19','-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)])
    return output
