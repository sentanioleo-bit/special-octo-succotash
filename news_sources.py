import re
from datetime import datetime, timezone
import feedparser

FEEDS = {
    'India': [
        ('Google News India', 'https://news.google.com/rss/search?q=India&hl=en-IN&gl=IN&ceid=IN:en'),
        ('Google News Business India', 'https://news.google.com/rss/search?q=India+business&hl=en-IN&gl=IN&ceid=IN:en'),
        ('Google News Stocks India', 'https://news.google.com/rss/search?q=India+stocks+market&hl=en-IN&gl=IN&ceid=IN:en'),
    ],
    'Global': [
        ('Google News World', 'https://news.google.com/rss/search?q=world+news&hl=en-IN&gl=IN&ceid=IN:en'),
        ('Google News Technology', 'https://news.google.com/rss/search?q=technology+AI&hl=en-IN&gl=IN&ceid=IN:en'),
        ('Google News Markets', 'https://news.google.com/rss/search?q=global+markets&hl=en-IN&gl=IN&ceid=IN:en'),
    ],
}

def clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()

def collect_news(limit_per_feed=12):
    rows = []
    for category, feeds in FEEDS.items():
        for feed_name, url in feeds:
            try:
                parsed = feedparser.parse(url)
                for e in parsed.entries[:limit_per_feed]:
                    title = clean(e.get('title'))
                    link = e.get('link', '')
                    summary = clean(re.sub('<[^>]+>', ' ', e.get('summary', '')))
                    if not title or not link:
                        continue
                    rows.append({
                        'category': category,
                        'title': title,
                        'summary': summary[:1200],
                        'link': link,
                        'feed_source': feed_name,
                        'published': e.get('published', ''),
                        'collected_at': datetime.now(timezone.utc).isoformat(),
                    })
            except Exception as exc:
                print(f'[WARN] feed failed: {feed_name}: {exc}')
    # Dedupe near-identical headlines while preserving multiple sources.
    seen, out = set(), []
    for row in rows:
        key = re.sub(r'[^a-z0-9]+', ' ', row['title'].lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out

if __name__ == '__main__':
    data = collect_news()
    print(f'Collected {len(data)} items')
    for i, x in enumerate(data[:20], 1): print(i, x['title'])
