from __future__ import annotations

from src.alerts.base import AlertChannel
from src.alerts.discord import DiscordAlert
from src.alerts.telegram import TelegramAlert


def create_alert_channels(config) -> list[AlertChannel]:
    channels: list[AlertChannel] = []
    if not config.alerts:
        return channels

    tg = config.alerts.get("telegram", {})
    if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
        channels.append(TelegramAlert(tg["bot_token"], tg["chat_id"]))

    dc = config.alerts.get("discord", {})
    if dc.get("enabled") and dc.get("webhook_url"):
        channels.append(DiscordAlert(dc["webhook_url"]))

    return channels
