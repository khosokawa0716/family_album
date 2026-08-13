"""
line_notify.send_line_broadcast のユニットテスト

LINE Messaging APIへの実際のHTTPリクエストは送信せず、httpx.AsyncClient.postを
モックして検証する。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from line_notify import send_line_broadcast


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
