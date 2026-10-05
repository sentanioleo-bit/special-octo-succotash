import os
import re
from datetime import datetime, timezone


INDIA_HASHTAGS = [
    "#Nifty50", "#Sensex", "#IndianStockMarket", "#StockMarketIndia",
    "#ShareMarket", "#MarketNews", "#Trading", "#Finance",
]
GLOBAL_HASHTAGS = [
    "#GlobalMarkets", "#WallStreet", "#StockMarket", "#MarketNews",
    "#Nasdaq", "#SP500", "#Investing", "#Finance",
]


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def build_youtube_metadata(edition: str, stories: list[dict]) -> dict:
    """Create upload-ready title, description, hashtags, and tags from today's actual stories."""
    edition = edition.lower()
    headlines = [_clean(s.get("headline", "")) for s in stories if _clean(s.get("headline", ""))]
    if not headlines:
        headlines = [f"{edition.title()} Market News"]

    lead = headlines[0].rstrip(".!?")
    date_label = datetime.now(timezone.utc).strftime("%d %b %Y")
    prefix = "India Market Today" if edition == "india" else "Global Markets Today"
    title = f"{prefix}: {lead} | Daily Market Briefing"
    if len(title) > 98:
        title = f"{prefix}: {lead[:max(20, 98 - len(prefix) - 30)].rstrip()}… | Market News"

    hashtags = INDIA_HASHTAGS if edition == "india" else GLOBAL_HASHTAGS
    topic_lines = "\n".join(f"• {headline}" for headline in headlines[:8])
    region = "Indian markets" if edition == "india" else "global financial markets"
    description = (
        f"{date_label} | Your concise daily briefing on {region}.\n\n"
        f"IN THIS VIDEO\n{topic_lines}\n\n"
        "Get the key headlines, market developments, and company news in one quick briefing. "
        "This video is for news and educational purposes only; it is not investment advice. "
        "Verify facts and consult a qualified professional before making financial decisions.\n\n"
        "Subscribe for regular market updates.\n\n"
        + " ".join(hashtags)
    )

    # YouTube's tag field has a 500-character limit. Keep tags relevant to this edition
    # and add words from today's real headlines instead of using a fixed tag list only.
    base_tags = (
        ["India stock market", "Nifty 50", "Sensex", "Indian market news",
         "share market today", "stock market India", "market analysis", "finance news"]
        if edition == "india"
        else ["global markets", "Wall Street", "US stock market", "Nasdaq",
              "S&P 500", "world market news", "global economy", "finance news"]
    )
    topic_tags = []
    for headline in headlines[:5]:
        words = re.findall(r"[A-Za-z0-9]+", headline)
        phrase = " ".join(words[:5])
        if len(phrase) >= 4:
            topic_tags.append(phrase)
    tags = []
    for tag in base_tags + topic_tags:
        if tag.lower() not in {t.lower() for t in tags}:
            tags.append(tag)
    tag_string = ", ".join(tags)[:500].rstrip(" ,")

    return {
        "yt_title": title[:100],
        "yt_description": description,
        "yt_tags": tag_string,
        "hashtags": " ".join(hashtags),
    }


def write_youtube_metadata(metadata: dict, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("YOUTUBE TITLE\n")
        f.write(metadata["yt_title"] + "\n\n")
        f.write("YOUTUBE DESCRIPTION (copy/paste)\n")
        f.write(metadata["yt_description"] + "\n\n")
        f.write("YOUTUBE TAGS (paste into Tags field; comma-separated)\n")
        f.write(metadata["yt_tags"] + "\n")
