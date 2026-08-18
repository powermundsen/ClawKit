"""Small Telegram Bot API client that never exposes the bot token."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
_TOKEN_RE = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{20,}$")


class TelegramError(RuntimeError):
    """Sanitized Telegram failure suitable for local categorization."""

    def __init__(self, category: str, http_status: int = 0) -> None:
        super().__init__(category)
        self.category = category
        self.http_status = http_status


Transport = Callable[[urllib.request.Request, float], bytes]


def _default_transport(request: urllib.request.Request, timeout: float) -> bytes:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise TelegramError("response_too_large")
    return data


class TelegramClient:
    def __init__(
        self,
        token: str,
        *,
        timeout_seconds: float = 20,
        transport: Transport = _default_transport,
    ) -> None:
        if not _TOKEN_RE.fullmatch(token):
            raise ValueError("invalid Telegram bot token format")
        self.__token = token
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def call(
        self,
        method: str,
        payload: Mapping[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> Any:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{1,63}", method):
            raise ValueError("invalid Telegram method")
        url = f"https://api.telegram.org/bot{self.__token}/{method}"
        body = json.dumps(dict(payload or {}), separators=(",", ":")).encode()
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            raw = self.transport(
                request,
                self.timeout_seconds if timeout_seconds is None else timeout_seconds,
            )
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            raise TelegramError("http_error", status) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise TelegramError("network_error") from None
        try:
            response = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise TelegramError("invalid_response") from None
        if not isinstance(response, dict) or not response.get("ok"):
            status = int(response.get("error_code", 0) or 0) if isinstance(response, dict) else 0
            raise TelegramError("api_error", status)
        return response.get("result")

    def get_me(self) -> dict[str, Any]:
        result = self.call("getMe")
        if not isinstance(result, dict):
            raise TelegramError("invalid_response")
        return result

    def get_updates(
        self,
        *,
        offset: int,
        long_poll_seconds: int = 25,
    ) -> list[dict[str, Any]]:
        result = self.call(
            "getUpdates",
            {
                "offset": offset,
                "timeout": long_poll_seconds,
                "allowed_updates": ["message"],
            },
            timeout_seconds=long_poll_seconds + 10,
        )
        if not isinstance(result, list):
            raise TelegramError("invalid_response")
        return [item for item in result if isinstance(item, dict)]

    def send_message(self, chat_id: int, html_text: str) -> int:
        result = self.call(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": html_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        if not isinstance(result, dict):
            raise TelegramError("invalid_response")
        return int(result.get("message_id", 0) or 0)

    def send_typing(self, chat_id: int) -> None:
        self.call(
            "sendChatAction",
            {"chat_id": chat_id, "action": "typing"},
        )
