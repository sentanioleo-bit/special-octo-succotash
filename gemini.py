import json
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_STORIES

SCHEMA = {
  'type': 'object', 'properties': {
    'title': {'type':'string'}, 'hook': {'type':'string'},
    'stories': {'type':'array','minItems':10,'maxItems':10,'items':{
      'type':'object','properties':{
        'headline':{'type':'string'}, 'category':{'type':'string'},
        'narration':{'type':'string'}, 'visual_plan':{'type':'array','items':{
          'type':'object','properties':{
            'duration':{'type':'number'}, 'type':{'type':'string'},
            'prompt':{'type':'string'}, 'overlay':{'type':'string'}
          },'required':['duration','type','prompt','overlay']
        }},
        'source':{'type':'string'}, 'source_url':{'type':'string'},
        'why_it_matters':{'type':'string'}
      },'required':['headline','category','narration','visual_plan','source','source_url','why_it_matters']
    }},
    'ending': {'type':'string'}
  }, 'required':['title','hook','stories','ending']
}

SYSTEM = '''You are the senior producer and fact-checking editor of a premium Indian digital news briefing.
Create an ORIGINAL, neutral, 3-minute vertical news package from supplied RSS material.

FORMAT: 9:16, 1080x1920, about 180 seconds, 10 stories.
Target 32-42 spoken words per story. Hook 12-18 words. Ending 10-16 words.

EDITORIAL:
- Never invent facts, quotes, numbers, sources or events.
- Use only information supported by supplied items.
- Prefer facts that appear in multiple independent source items.
- If a claim is uncertain or sources disagree, say so briefly.
- Do not copy article sentences; rewrite in original language.
- For stocks/markets, report facts and clearly label interpretation; no personalized financial advice.
- Each story must answer WHAT happened + WHY it matters.
- Natural spoken English, concise, calm, energetic, trustworthy.

VISUAL DIRECTOR:
For each story create 3 shots totaling about 17-18 seconds.
Use a mixture of: real-photo, stock-video, chart, map, infographic, ai-video.
Only request ai-video for visually useful generic scenes that do NOT fabricate real breaking-news footage.
Never ask AI video to depict a real person as if they were actually present at a breaking event.
Avoid logos and unreadable text in generated footage.
Each AI-video prompt must describe one self-contained 6-8 second cinematic shot.
Overlay text must be <= 7 words.

The final result must be valid JSON matching the schema.'''

def build_prompt(items):
    compact = [{k:x.get(k,'') for k in ('category','title','summary','feed_source','link','published')} for x in items]
    return SYSTEM + '\n\nSOURCE MATERIAL:\n' + json.dumps(compact, ensure_ascii=False)

def generate_briefing(items):
    if not GEMINI_API_KEY: raise RuntimeError('GEMINI_API_KEY is missing')
    client = genai.Client(api_key=GEMINI_API_KEY)
    r = client.models.generate_content(
        model=GEMINI_MODEL, contents=build_prompt(items),
        config=types.GenerateContentConfig(response_mime_type='application/json', response_schema=SCHEMA, temperature=0.35)
    )
    data = json.loads(r.text)
    if len(data.get('stories', [])) != MAX_STORIES: raise ValueError('Expected exactly 10 stories')
    return data
