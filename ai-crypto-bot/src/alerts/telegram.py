from __future__ import annotations

import httpx

from src.alerts.base import AlertChannel


class TelegramAlert(AlertChannel):
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.chat_id = chat_id

    async def send(self, message: str) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                self.url,
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
            )
