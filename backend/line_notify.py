import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"


def get_display_name(user_name: Optional[str], nickname: Optional[str]) -> str:
    """通知に表示する投稿者名を決定する。ニックネーム優先（frontendのgetDisplayNameと同じ方針）。"""
    if nickname and nickname.strip():
        return nickname
    return user_name or "不明"


def build_upload_notification_message(
    media_type: str,
    count: int,
    title: Optional[str],
    user_name: Optional[str],
    nickname: Optional[str],
    group_id: str,
) -> str:
    """写真・動画アップロード時のLINE通知メッセージを組み立てる。

    media_type: "photo" または "video"
    count: 同時投稿された枚数（動画は常に1）
    """
    if media_type == "video":
        header = "新しい動画が投稿されました"
    elif count > 1:
        header = f"写真が{count}枚投稿されました"
    else:
        header = "新しい写真が投稿されました"

    lines = [header]

    if title and title.strip():
        lines.append(f"タイトル: {title.strip()}")

    lines.append(f"投稿者: {get_display_name(user_name, nickname)}")

    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        # #openExternalBrowser=1 を付けることで、LINEアプリ内蔵ブラウザではなく端末の
        # 標準ブラウザで開かせる。内蔵ブラウザはタップごとに保存領域が独立しており、
        # ログイン状態（localStorage）を維持できないため。
        lines.append(f"{frontend_url.rstrip('/')}/photo/detail/{group_id}#openExternalBrowser=1")
    else:
        logger.info("FRONTEND_URL is not set; skipping detail URL in LINE notification")

    return "\n".join(lines)


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
