import os
import time
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import feedparser

SEEN_CACHE_FILE = "work/seen_headlines.json"

INDIA_FEEDS = [
    "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.livemint.com/rss/markets",
    "https://feeds.feedburner.com/ndtvprofit-latest"
]

GLOBAL_FEEDS = [
    "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=markets",
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://www.investing.com/rss/news_25.rss",
    "https://finance.yahoo.com/news/rssindex"
]

def load_seen_cache() -> Dict[str, float]:
    if os.path.exists(SEEN_CACHE_FILE):
        try:
            with open(SEEN_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_seen_cache(cache: Dict[str, float]):
    os.makedirs(os.path.dirname(SEEN_CACHE_FILE), exist_ok=True)
    with open(SEEN_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def clean_old_cache(cache: Dict[str, float], max_days: int = 3) -> Dict[str, float]:
    cutoff = time.time() - (max_days * 86400)
    return {k: v for k, v in cache.items() if v > cutoff}

def get_hash(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()

def fetch_market_news(edition: str = "india", hours_fresh: int = 24) -> List[Dict[str, Any]]:
    feeds = INDIA_FEEDS if edition.lower() == "india" else GLOBAL_FEEDS
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_fresh)
    
    seen_cache = clean_old_cache(load_seen_cache())
    fresh_stories = []

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                if not title or len(title) < 15:
                    continue

                h = get_hash(title)
                if h in seen_cache:
                    continue

                pub_time = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_time = datetime.fromtimestamp(time.mktime(entry.published_parsed), timezone.utc)
                
                # Check freshness cutoff
                if pub_time and pub_time < cutoff:
                    continue

                summary = entry.get("summary", "") or entry.get("description", "")
                fresh_stories.append({
                    "title": title,
                    "summary": summary[:400],
                    "link": entry.get("link", ""),
                    "published": pub_time.isoformat() if pub_time else None
                })
                seen_cache[h] = time.time()
        except Exception as e:
            print(f"Error reading {feed_url}: {e}")

    save_seen_cache(seen_cache)
    return fresh_stories
    
