import logging
from typing import Any, Dict, List

import feedparser

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; MarketBriefBot/1.0)"

INDIA_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "https://www.livemint.com/rss/markets",
]

GLOBAL_FEEDS = [
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=markets&category=markets&format=rss",
    "https://feeds.bloomberg.com/markets/news.rss",
]


def fetch_market_news(edition: str = "india") -> List[Dict[str, Any]]:
    feeds = INDIA_FEEDS if edition.lower() == "india" else GLOBAL_FEEDS
    items: List[Dict[str, Any]] = []
    seen = set()

    for url in feeds:
        try:
            feed = feedparser.parse(url, agent=USER_AGENT)
            for entry in feed.entries[:8]:
                title = (entry.get("title") or "").strip()
