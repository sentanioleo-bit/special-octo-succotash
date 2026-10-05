import argparse
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser

logger = logging.getLogger(**name**)

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

def _normalise_title(title: str) -> str:
"""Normalize headlines for basic duplicate detection."""
return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()

def _published_datetime(entry: Any) -> datetime | None:
"""Read the publication date from common RSS date fields."""
for field in ("published_parsed", "updated_parsed"):
value = entry.get(field)
if value:
try:
from time import struct_time, mktime
import calendar

```
            # RSS parsed dates are generally UTC.
            return datetime.fromtimestamp(
                calendar.timegm(value), tz=timezone.utc
            )
        except (TypeError, ValueError, OverflowError):
            pass

for field in ("published", "updated", "pubDate"):
    value = entry.get(field)
    if value:
        try:
            result = parsedate_to_datetime(value)
            if result.tzinfo is None:
                result = result.replace(tzinfo=timezone.utc)
            return result.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            continue

return None
```

def fetch_market_news(
edition: str = "india",
max_age_hours: int = 48,
limit: int = 20,
) -> list[dict[str, Any]]:
"""Fetch recent RSS stories for the India or global edition."""
edition = edition.strip().lower()

```
if edition not in {"india", "global"}:
    raise ValueError("edition must be 'india' or 'global'")

if max_age_hours < 1 or limit < 1:
    raise ValueError("max_age_hours and limit must be positive")

feeds = INDIA_FEEDS if edition == "india" else GLOBAL_FEEDS
cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
items: list[dict[str, Any]] = []
seen: set[str] = set()

for url in feeds:
    try:
        feed = feedparser.parse(
            url,
            agent=USER_AGENT,
            request_headers={"User-Agent": USER_AGENT},
        )

        if getattr(feed, "bozo", False):
            logger.warning("Feed parsing warning for %s", url)

        source = (
            feed.feed.get("title")
            or re.sub(r"^https?://", "", url).split("/")[0]
        )

        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            if not title:
                continue

            key = _normalise_title(title)
            if not key or key in seen:
                continue

            published = _published_datetime(entry)

            # Skip stories with no date or stories older than the cutoff.
            # This avoids silently presenting old articles as breaking news.
            if published is None or published < cutoff:
                continue

            seen.add(key)
            summary = (
                entry.get("summary")
                or entry.get("description")
                or ""
            ).strip()

            items.append(
                {
                    "title": title,
                    "summary": summary[:500],
                    "source": source,
                    "published": published.isoformat(),
                    "link": entry.get("link", ""),
                }
            )

    except Exception:
        logger.exception("Failed fetching feed %s", url)

items.sort(key=lambda item: item["published"], reverse=True)
result = items[:limit]

logger.info(
    "Collected %d recent stories for %s",
    len(result),
    edition.upper(),
)
return result
```

def main() -> None:
parser = argparse.ArgumentParser(description="Test the market news collector")
parser.add_argument("--edition", choices=["india", "global"], default="india")
parser.add_argument("--max-age-hours", type=int, default=48)
parser.add_argument("--limit", type=int, default=20)
args = parser.parse_args()

```
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

stories = fetch_market_news(
    edition=args.edition,
    max_age_hours=args.max_age_hours,
    limit=args.limit,
)

if not stories:
    print("No recent dated stories found. Check RSS feed access or try a wider age window.")
    return

for index, story in enumerate(stories, start=1):
    print(f"\n{index}. {story['title']}")
    print(f"   Source: {story['source']}")
    print(f"   Published: {story['published']}")
    print(f"   Link: {story['link']}")
    if story["summary"]:
        print(f"   Summary: {story['summary']}")
```

if **name** == "**main**":
main()
