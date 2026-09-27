import json
from pathlib import Path
from news_sources import collect_news
from gemini import generate_briefing
from providers import get_visual
from tts import synthesize
from render import render_video, fallback_card
from telegram import send_video
from config import WORK,MAX_STORIES

def main():
    items=collect_news()
    if len(items)<MAX_STORIES: raise RuntimeError(f'Only {len(items)} usable news items found')
    briefing=generate_briefing(items)
    (WORK/'briefing.json').write_text(json.dumps(briefing,ensure_ascii=False,indent=2),encoding='utf-8')
    story_assets={}; ai_used=0
    for i,story in enumerate(briefing['stories'],1):
        story_assets[i]=[]
        for j,shot in enumerate(story['visual_plan'][:3],1):
            p,ai_used=get_visual(shot['prompt'],i*10+j,ai_used)
            if not p:
                card=WORK/f'fallback_{i}_{j}.jpg'; fallback_card(card,story['category'],story['headline'],shot.get('overlay','')); p={'path':str(card),'type':'image'}
            p['duration']=float(shot.get('duration',6)); story_assets[i].append(p)
    # Ensure enough runtime: the renderer trims at 180s.
    narration=' '.join([briefing['hook']]+[s['narration'] for s in briefing['stories']]+[briefing['ending']])
    audio=synthesize(narration,WORK/'narration.wav')
    video=render_video(briefing,audio,story_assets)
    send_video(video,briefing['title'])
    print(f'AI video clips used: {ai_used}')
    print(f'OUTPUT: {video}')

if __name__=='__main__': main()
