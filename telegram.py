import os
import requests
import logging

logger = logging.getLogger(__name__)

def send_video_to_telegram(video_path: str, briefing_data: dict, edition: str = "india"):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.info("[INFO] Telegram secrets not set: skipping upload")
        return False

    if not os.path.exists(video_path):
        logger.error(f"Cannot find video file: {video_path}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendVideo"

    yt_title = briefing_data.get("yt_title", f"{edition.upper()} Stock Market Top 10 Today")
    yt_desc = briefing_data.get("yt_description", "")
    
    tags = "#Nifty50 #Sensex #StockMarketIndia #Trading #ShareMarket" if edition == "india" else "#StockMarket #WallStreet #Trading #Nasdaq #Finance"

    caption = (
        f"📊 **{edition.upper()} MARKET TOP 10**\n\n"
        f"**Suggested YT Title:**\n`{yt_title}`\n\n"
        f"**Description & Tags:**\n{yt_desc}\n\n"
        f"{tags}"
    )

    if len(caption) > 1000:
        caption = caption[:995] + "..."

    logger.info(f"Dispatching video to Telegram...")

    with open(video_path, "rb") as video_file:
        files = {"video": video_file}
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "Markdown",
            "supports_streaming": True
        }
        res = requests.post(url, data=data, files=files, timeout=300)

    if res.status_code == 200:
        logger.info("Video successfully delivered to Telegram!")
        return True
    else:
        logger.error(f"Telegram upload failed: {res.status_code} - {res.text}")
        return False
        
