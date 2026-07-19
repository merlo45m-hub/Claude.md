from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AlertChannel(ABC):
    @abstractmethod
    async def send(self, message: str) -> None: ...

    async def safe_send(self, message: str) -> None:
        try:
            await self.send(message)
        except Exception:
            logger.warning("Alert send failed (%s)", self.__class__.__name__, exc_info=True)
