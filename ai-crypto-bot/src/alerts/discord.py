from __future__ import annotations

import httpx

from src.alerts.base import AlertChannel


class DiscordAlert(AlertChannel):
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def send(self, message: str) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                self.webhook_url,
                json={"content": message},
            )
