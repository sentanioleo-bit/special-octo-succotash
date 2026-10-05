import logging
import os

import requests

logger = logging.getLogger(__name__)


def send_video_to_telegram(
    video_path: str, briefing_data: dict, edition: str = "india"
) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.info("Telegram secrets not set; skipping direct video upload.")
        return False
    if not os.path.isfile(video_path) or os.path.getsize(video_path) == 0:
        logger.error("Video file is missing or empty: %s", video_path)
        return False

    yt_title = briefing_data.get(
        "yt_title", f"{edition.upper()} Market Briefing Today"
    )
    yt_desc = briefing_data.get("yt_description", "")
    tags = (
        "#Nifty50 #Sensex #StockMarketIndia #Trading #ShareMarket"
        if edition == "india"
        else "#GlobalMarkets #WallStreet #Trading #Nasdaq #Finance"
    )
    caption = (
        f"{edition.upper()} MARKET BRIEFING\n\n"
        f"Suggested YouTube title: {yt_title}\n\n"
        f"{yt_desc}\n\n{tags}"
    )
    caption = caption[:1000]

    url = f"https://api.telegram.org/bot{token}/sendVideo"
    try:
        logger.info("Uploading %s video to Telegram...", edition.upper())
        with open(video_path, "rb") as video_file:
            response = requests.post(
                url,
                data={
                    "chat_id": chat_id,
                    "caption": caption,
                    "supports_streaming": "true",
                },
                files={"video": (os.path.basename(video_path), video_file, "video/mp4")},
                timeout=(30, 300),
            )
        if response.ok and response.json().get("ok"):
            logger.info("Telegram video upload succeeded.")
            return True
        logger.error(
            "Telegram upload failed: HTTP %s: %s",
            response.status_code,
            response.text[:1000],
        )
    except (requests.RequestException, OSError, ValueError) as exc:
        logger.warning("Telegram upload failed; workflow can still publish a release link: %s", exc)
    return False


def send_message_to_telegram(metadata: dict, edition: str = "india") -> bool:
    """Send full upload-ready YouTube metadata as a separate Telegram message."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.info("Telegram secrets not set; skipping YouTube metadata message.")
        return False

    message = (
        f"📋 YOUTUBE UPLOAD PACK — {edition.upper()}\n\n"
        f"TITLE\n{metadata.get('yt_title', '')}\n\n"
        f"DESCRIPTION\n{metadata.get('yt_description', '')}\n\n"
        f"TAGS (copy into YouTube's Tags field)\n{metadata.get('yt_tags', '')}"
    )
    # Telegram sendMessage has a 4096-character text limit.
    message = message[:4000]
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message},
            timeout=30,
        )
        if response.ok and response.json().get("ok"):
            return True
        logger.warning("Telegram metadata message failed: HTTP %s: %s", response.status_code, response.text[:500])
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Telegram metadata message failed: %s", exc)
    return False
