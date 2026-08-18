from __future__ import annotations

import json
import unittest
import urllib.error
from typing import Any

from clawkit.bridge.telegram_client import TelegramClient, TelegramError

TOKEN = "123456789:abcdefghijklmnopqrstuvwxyzABCDE"


class RecordingTransport:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.urls: list[str] = []
        self.payloads: list[dict[str, Any]] = []

    def __call__(self, request: Any, timeout: float) -> bytes:
        self.urls.append(request.full_url)
        self.payloads.append(json.loads(request.data))
        return json.dumps(self.response).encode()


class TestTelegramClient(unittest.TestCase):
    def test_send_message_uses_html_and_returns_message_id(self) -> None:
        transport = RecordingTransport(
            {"ok": True, "result": {"message_id": 42}}
        )
        client = TelegramClient(TOKEN, transport=transport)

        message_id = client.send_message(1001, "<b>Hei</b>")

        self.assertEqual(message_id, 42)
        self.assertEqual(transport.payloads[0]["parse_mode"], "HTML")
        self.assertEqual(transport.payloads[0]["chat_id"], 1001)

    def test_http_error_never_contains_token(self) -> None:
        def failing_transport(request: Any, timeout: float) -> bytes:
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                f"token={TOKEN}",
                {},
                None,
            )

        client = TelegramClient(TOKEN, transport=failing_transport)

        with self.assertRaises(TelegramError) as raised:
            client.get_me()
        self.assertNotIn(TOKEN, str(raised.exception))
        self.assertEqual(raised.exception.http_status, 401)

    def test_invalid_token_and_method_are_rejected_before_network(self) -> None:
        with self.assertRaises(ValueError):
            TelegramClient("not-a-token")
        client = TelegramClient(TOKEN, transport=RecordingTransport({"ok": True}))
        with self.assertRaises(ValueError):
            client.call("../getMe")


if __name__ == "__main__":
    unittest.main()
