from __future__ import annotations

from src.alerts.base import AlertChannel
from src.alerts.discord import DiscordAlert


def create_alert_channels(config) -> list[AlertChannel]:
    channels: list[AlertChannel] = []
    if not config.alerts:
        return channels

    # Telegram alert removed per request — Discord only.
    dc = config.alerts.get("discord", {})
    if dc.get("enabled") and dc.get("webhook_url"):
        channels.append(DiscordAlert(dc["webhook_url"]))

    return channels
