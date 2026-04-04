from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from market_data.config import (
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_DEFAULT_CHAT_ID,
)

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    @abstractmethod
    async def send(self, recipient: str, subject: str, body: str) -> bool: ...

    @abstractmethod
    def is_configured(self) -> bool: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class TelegramChannel(NotificationChannel):
    def __init__(self, token: str | None = None, default_chat_id: str | None = None) -> None:
        self._token = token or TELEGRAM_BOT_TOKEN
        self._default_chat_id = default_chat_id or TELEGRAM_DEFAULT_CHAT_ID

    @property
    def name(self) -> str:
        return "telegram"

    def is_configured(self) -> bool:
        return self._token is not None

    async def send(self, recipient: str, subject: str, body: str) -> bool:
        if not self._token:
            logger.warning("telegram: token not configured, skipping")
            return False

        chat_id = recipient or self._default_chat_id
        if not chat_id:
            logger.warning("telegram: no chat_id provided and no default set, skipping")
            return False

        try:
            from telegram import Bot

            text = f"🔔 {subject}\n\n{body}"
            async with Bot(token=self._token) as bot:
                await bot.send_message(chat_id=int(chat_id), text=text)
            logger.info("telegram: sent to chat_id=%s", chat_id)
            return True
        except Exception:
            logger.exception("telegram: failed to send to chat_id=%s", chat_id)
            return False


class EmailChannel(NotificationChannel):
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        sender: str | None = None,
    ) -> None:
        self._host = host or SMTP_HOST
        self._port = port if port is not None else SMTP_PORT
        self._username = username or SMTP_USERNAME
        self._password = password or SMTP_PASSWORD
        self._sender = sender or SMTP_FROM or self._username

    @property
    def name(self) -> str:
        return "email"

    def is_configured(self) -> bool:
        return self._username is not None and self._password is not None

    async def send(self, recipient: str, subject: str, body: str) -> bool:
        if not self._username or not self._password:
            logger.warning("email: SMTP credentials not configured, skipping")
            return False
        if not recipient:
            logger.warning("email: no recipient provided, skipping")
            return False

        try:
            import aiosmtplib

            msg = MIMEMultipart("alternative")
            msg["From"] = self._sender or self._username
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            msg.attach(
                MIMEText(
                    f"<html><body><h3>{subject}</h3><p>{body}</p></body></html>",
                    "html",
                )
            )

            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
            )
            logger.info("email: sent to %s", recipient)
            return True
        except Exception:
            logger.exception("email: failed to send to %s", recipient)
            return False


class NotificationDispatcher:
    def __init__(self) -> None:
        self._channels: dict[str, NotificationChannel] = {}

    def register(self, channel: NotificationChannel) -> None:
        self._channels[channel.name] = channel

    def unregister(self, name: str) -> None:
        self._channels.pop(name, None)

    @property
    def available_channels(self) -> list[str]:
        return [name for name, ch in self._channels.items() if ch.is_configured()]

    async def dispatch(
        self,
        channels: list[str],
        recipient_map: dict[str, str],
        subject: str,
        body: str,
    ) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for ch_name in channels:
            ch = self._channels.get(ch_name)
            if ch is None:
                logger.warning("dispatch: unknown channel %r, skipping", ch_name)
                results[ch_name] = False
                continue
            if not ch.is_configured():
                logger.warning("dispatch: channel %r not configured, skipping", ch_name)
                results[ch_name] = False
                continue
            recipient = recipient_map.get(ch_name, "")
            results[ch_name] = await ch.send(recipient, subject, body)
        return results


_dispatcher: NotificationDispatcher | None = None


def get_dispatcher() -> NotificationDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = NotificationDispatcher()
        _dispatcher.register(TelegramChannel())
        _dispatcher.register(EmailChannel())
    return _dispatcher


def build_alert_message(alert_data: dict[str, Any]) -> tuple[str, str]:
    alert = alert_data["alert"]
    price = alert_data["price"]
    message: str = alert_data["message"]
    subject = f"Alert: {alert.ticker} — {alert.condition.value} {alert.threshold}"
    body = (
        f"{message}\n"
        f"Ticker: {alert.ticker}\n"
        f"Price: {price.close:.4f}\n"
        f"Condition: {alert.condition.value} {alert.threshold}\n"
    )
    return subject, body
