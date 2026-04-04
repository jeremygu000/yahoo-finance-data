from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from market_data.alerts import Alert, AlertCondition
from market_data.notifications import (
    EmailChannel,
    NotificationChannel,
    NotificationDispatcher,
    TelegramChannel,
    build_alert_message,
    get_dispatcher,
)
from market_data.schemas import PriceUpdate


class TestTelegramChannel:
    def test_not_configured_without_token(self) -> None:
        ch = TelegramChannel(token=None)
        assert not ch.is_configured()

    def test_configured_with_token(self) -> None:
        ch = TelegramChannel(token="fake-token")
        assert ch.is_configured()

    def test_name(self) -> None:
        ch = TelegramChannel(token="fake-token")
        assert ch.name == "telegram"

    @pytest.mark.asyncio
    async def test_send_skips_when_no_token(self) -> None:
        ch = TelegramChannel(token=None)
        result = await ch.send("12345", "Test", "body")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_skips_when_no_chat_id(self) -> None:
        ch = TelegramChannel(token="fake-token", default_chat_id=None)
        result = await ch.send("", "Test", "body")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_success(self) -> None:
        mock_bot_instance = AsyncMock()
        mock_bot_instance.send_message = AsyncMock()
        mock_bot_instance.__aenter__ = AsyncMock(return_value=mock_bot_instance)
        mock_bot_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("market_data.notifications.TelegramChannel.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            ch = TelegramChannel(token="fake-token")
            result = await mock_send("12345", "Test Subject", "Test body")
            assert result is True

    @pytest.mark.asyncio
    async def test_send_uses_default_chat_id(self) -> None:
        ch = TelegramChannel(token="fake-token", default_chat_id="99999")
        with patch("market_data.notifications.TelegramChannel.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await mock_send("", "Test", "body")
            assert result is True


class TestEmailChannel:
    def test_not_configured_without_credentials(self) -> None:
        ch = EmailChannel(username=None, password=None)
        assert not ch.is_configured()

    def test_configured_with_credentials(self) -> None:
        ch = EmailChannel(username="user@test.com", password="pass")
        assert ch.is_configured()

    def test_name(self) -> None:
        ch = EmailChannel(username="u", password="p")
        assert ch.name == "email"

    @pytest.mark.asyncio
    async def test_send_skips_when_no_credentials(self) -> None:
        ch = EmailChannel(username=None, password=None)
        result = await ch.send("to@test.com", "Test", "body")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_skips_when_no_recipient(self) -> None:
        ch = EmailChannel(username="user@test.com", password="pass")
        result = await ch.send("", "Test", "body")
        assert result is False


class TestNotificationDispatcher:
    def test_register_and_available(self) -> None:
        d = NotificationDispatcher()
        ch = TelegramChannel(token="fake")
        d.register(ch)
        assert "telegram" in d.available_channels

    def test_unconfigured_not_in_available(self) -> None:
        d = NotificationDispatcher()
        ch = TelegramChannel(token=None)
        d.register(ch)
        assert "telegram" not in d.available_channels

    def test_unregister(self) -> None:
        d = NotificationDispatcher()
        ch = TelegramChannel(token="fake")
        d.register(ch)
        d.unregister("telegram")
        assert "telegram" not in d.available_channels

    @pytest.mark.asyncio
    async def test_dispatch_unknown_channel(self) -> None:
        d = NotificationDispatcher()
        results = await d.dispatch(["nonexistent"], {}, "sub", "body")
        assert results == {"nonexistent": False}

    @pytest.mark.asyncio
    async def test_dispatch_unconfigured_channel(self) -> None:
        d = NotificationDispatcher()
        d.register(TelegramChannel(token=None))
        results = await d.dispatch(["telegram"], {"telegram": "123"}, "sub", "body")
        assert results == {"telegram": False}

    @pytest.mark.asyncio
    async def test_dispatch_calls_send(self) -> None:
        d = NotificationDispatcher()
        mock_ch = AsyncMock(spec=NotificationChannel)
        mock_ch.name = "mock"
        mock_ch.is_configured.return_value = True
        mock_ch.send.return_value = True
        d.register(mock_ch)
        results = await d.dispatch(["mock"], {"mock": "recipient"}, "sub", "body")
        assert results == {"mock": True}
        mock_ch.send.assert_awaited_once_with("recipient", "sub", "body")


class TestBuildAlertMessage:
    def test_build_message(self) -> None:
        alert = Alert(ticker="AAPL", condition=AlertCondition.above, threshold=200.0)
        price = PriceUpdate(
            ticker="AAPL", date="2025-01-01", open=190.0, high=210.0, low=185.0, close=205.0, volume=1000
        )
        item: dict[str, Any] = {"alert": alert, "price": price, "message": "AAPL crossed above 200.0"}
        subject, body = build_alert_message(item)
        assert "AAPL" in subject
        assert "above" in subject
        assert "205.0000" in body
        assert "AAPL" in body


class TestGetDispatcher:
    def test_singleton(self) -> None:
        d1 = get_dispatcher()
        d2 = get_dispatcher()
        assert d1 is d2

    def test_has_default_channels(self) -> None:
        d = get_dispatcher()
        assert "telegram" in d._channels
        assert "email" in d._channels
