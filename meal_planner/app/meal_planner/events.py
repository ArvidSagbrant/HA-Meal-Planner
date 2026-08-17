"""Small in-process change notification hub for optional integrations."""

from __future__ import annotations

import logging
from collections.abc import Callable


LOGGER = logging.getLogger(__name__)


class ChangeNotifier:
    def __init__(self) -> None:
        self._subscribers: list[Callable[[], None]] = []

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._subscribers.append(callback)

    def notify(self) -> None:
        for callback in tuple(self._subscribers):
            try:
                callback()
            except Exception:
                LOGGER.exception("An integration failed while handling an application change")
