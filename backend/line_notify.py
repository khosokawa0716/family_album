import os
import logging

import httpx

logger = logging.getLogger(__name__)

LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"


async def send_line_broadcast(message: str) -> bool:
    """LINE公式アカウントの友だち全員にテキストメッセージをブロードキャスト送信する。

    LINE_CHANNEL_ACCESS_TOKEN未設定時は送信をスキップする。送信失敗時も例外は
    投げず、呼び出し元の処理（アップロード等）をブロックしないようにする。
    """
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        logger.info("LINE_CHANNEL_ACCESS_TOKEN is not set; skipping LINE notification")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {"messages": [{"type": "text", "text": message}]}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(LINE_BROADCAST_URL, headers=headers, json=payload)

        if response.status_code != 200:
            logger.error(f"LINE broadcast failed: status={response.status_code}, body={response.text}")
            return False

        return True

    except httpx.HTTPError as e:
        logger.error(f"LINE broadcast request failed: {e}")
        return False
