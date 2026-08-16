"""
line_notify モジュールのユニットテスト

LINE Messaging APIへの実際のHTTPリクエストは送信せず、httpx.AsyncClient.postを
モックして検証する。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from line_notify import send_line_broadcast, build_upload_notification_message, get_display_name


class TestSendLineBroadcast:
    def test_skips_when_token_not_set(self, monkeypatch):
        monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            result = asyncio.run(send_line_broadcast("test message"))

        assert result is False
        mock_post.assert_not_awaited()

    def test_returns_true_and_sends_expected_payload_on_success(self, monkeypatch):
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy-token")
        mock_response = MagicMock(status_code=200)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = asyncio.run(send_line_broadcast("新しい写真が投稿されました"))

        assert result is True
        mock_post.assert_awaited_once()
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer dummy-token"
        assert kwargs["json"]["messages"][0]["text"] == "新しい写真が投稿されました"

    def test_returns_false_on_non_200_response(self, monkeypatch):
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy-token")
        mock_response = MagicMock(status_code=401, text="Invalid channel access token")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = asyncio.run(send_line_broadcast("test message"))

        assert result is False

    def test_returns_false_on_request_error(self, monkeypatch):
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy-token")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.ConnectError("boom")):
            result = asyncio.run(send_line_broadcast("test message"))

        assert result is False


class TestGetDisplayName:
    def test_prefers_nickname_when_present(self):
        assert get_display_name("taro_yamada", "たろう") == "たろう"

    def test_falls_back_to_user_name_when_nickname_blank(self):
        assert get_display_name("taro_yamada", "  ") == "taro_yamada"
        assert get_display_name("taro_yamada", None) == "taro_yamada"

    def test_falls_back_to_unknown_when_both_missing(self):
        assert get_display_name(None, None) == "不明"


class TestBuildUploadNotificationMessage:
    def test_single_photo_with_title_and_url(self, monkeypatch):
        monkeypatch.setenv("FRONTEND_URL", "http://album.local")

        message = build_upload_notification_message(
            media_type="photo",
            count=1,
            title="海水浴",
            user_name="taro_yamada",
            nickname="たろう",
            group_id="abc-123",
        )

        assert message == (
            "新しい写真が投稿されました\n"
            "タイトル: 海水浴\n"
            "投稿者: たろう\n"
            "http://album.local/photo/detail/abc-123#openExternalBrowser=1"
        )

    def test_multiple_photos_shows_count_in_header(self, monkeypatch):
        monkeypatch.delenv("FRONTEND_URL", raising=False)

        message = build_upload_notification_message(
            media_type="photo",
            count=3,
            title=None,
            user_name="taro_yamada",
            nickname=None,
            group_id="abc-123",
        )

        assert message == "写真が3枚投稿されました\n投稿者: taro_yamada"

    def test_video_header_ignores_count(self, monkeypatch):
        monkeypatch.delenv("FRONTEND_URL", raising=False)

        message = build_upload_notification_message(
            media_type="video",
            count=1,
            title=None,
            user_name="taro_yamada",
            nickname=None,
            group_id="abc-123",
        )

        assert message.startswith("新しい動画が投稿されました")

    def test_omits_url_when_frontend_url_not_set(self, monkeypatch):
        monkeypatch.delenv("FRONTEND_URL", raising=False)

        message = build_upload_notification_message(
            media_type="photo",
            count=1,
            title=None,
            user_name="taro_yamada",
            nickname=None,
            group_id="abc-123",
        )

        assert "http" not in message

    def test_strips_trailing_slash_from_frontend_url(self, monkeypatch):
        monkeypatch.setenv("FRONTEND_URL", "http://album.local/")

        message = build_upload_notification_message(
            media_type="photo",
            count=1,
            title=None,
            user_name="taro_yamada",
            nickname=None,
            group_id="abc-123",
        )

        assert "http://album.local/photo/detail/abc-123#openExternalBrowser=1" in message
        assert "http://album.local//photo" not in message
