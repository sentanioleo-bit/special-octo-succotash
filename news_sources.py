import feedparser
from datetime import datetime, timezone


NEWS_SOURCES = {
    "India": [
        "https://news.google.com/rss/search?q=India&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=India+business&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=India+stocks&hl=en-IN&gl=IN&ceid=IN:en",
    ],
    "Global": [
        "https://news.google.com/rss/search?q=world+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=global+business&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=AI+technology&hl=en-IN&gl=IN&ceid=IN:en",
    ],
}


def collect_news():
    stories = []

    for category, feeds in NEWS_SOURCES.items():
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)

            for item in feed.entries[:10]:
                title = item.get("title", "").strip()
                link = item.get("link", "").strip()
                source = item.get("source", {}).get("title", "Google News")

                if not title or not link:
                    continue

                stories.append({
                    "category": category,
                    "title": title,
                    "link": link,
                    "source": source,
                    "collected_at": datetime.now(timezone.utc).isoformat()
                })

    return stories


if __name__ == "__main__":
    stories = collect_news()

    for i, story in enumerate(stories[:20], start=1):
        print(f"{i}. [{story['category']}] {story['title']}")
        print(f"   {story['link']}")
        print()
