"""Resilient MQTT publisher lifecycle backed by Eclipse Paho."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from threading import Lock
from typing import Any

import paho.mqtt.client as mqtt

from ..config import MqttSettings
from ..schemas import PlanDay
from ..services.plans import PlanService
from .discovery import (
    MqttMessage,
    availability_topic,
    discovery_messages,
    state_messages,
)


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MqttIntegrationStatus:
    enabled: bool
    connected: bool
    mode: str
    broker: str | None
    last_error: str | None


class MqttIntegration:
    def __init__(
        self,
        settings: MqttSettings,
        plans: PlanService,
        language: str,
        *,
        client_factory: Callable[[], Any] | None = None,
        date_provider: Callable[[], date] = date.today,
    ) -> None:
        self.settings = settings
        self.plans = plans
        self.language = language
        self._client_factory = client_factory or self._create_client
        self._date_provider = date_provider
        self._client: Any | None = None
        self._connected = False
        self._last_error: str | None = None
        self._lock = Lock()

    def start(self) -> None:
        if not self.settings.enabled:
            LOGGER.info("MQTT integration is disabled")
            return
        try:
            client = self._client_factory()
            client.on_connect = self._on_connect
            client.on_connect_fail = self._on_connect_fail
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            client.reconnect_delay_set(min_delay=1, max_delay=60)
            client.will_set(
                availability_topic(self.settings),
                payload="offline",
                qos=1,
                retain=True,
            )
            if self.settings.username:
                client.username_pw_set(
                    self.settings.username,
                    self.settings.password or None,
                )
            if self.settings.tls:
                client.tls_set()
            self._client = client
            client.connect_async(self.settings.host, self.settings.port, keepalive=60)
            client.loop_start()
            LOGGER.info(
                "Connecting to MQTT broker %s:%s (%s)",
                self.settings.host,
                self.settings.port,
                self.settings.mode,
            )
        except Exception as error:
            self._set_error(f"MQTT startup failed: {error}")
            LOGGER.exception("Could not start MQTT integration")

    def stop(self) -> None:
        client = self._client
        if client is None:
            return
        try:
            if self._is_connected():
                client.publish(
                    availability_topic(self.settings),
                    payload="offline",
                    qos=1,
                    retain=True,
                )
            client.disconnect()
            client.loop_stop()
        except Exception:
            LOGGER.exception("Could not stop MQTT integration cleanly")
        finally:
            with self._lock:
                self._connected = False
            self._client = None

    def publish_state(self) -> None:
        if not self._is_connected():
            return
        self._publish(self._build_state_messages())

    def status(self) -> MqttIntegrationStatus:
        with self._lock:
            return MqttIntegrationStatus(
                enabled=self.settings.enabled,
                connected=self._connected,
                mode=self.settings.mode,
                broker=(
                    f"{self.settings.host}:{self.settings.port}"
                    if self.settings.enabled
                    else None
                ),
                last_error=self._last_error,
            )

    @staticmethod
    def _create_client() -> mqtt.Client:
        return mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="meal_planner_addon",
            protocol=mqtt.MQTTv311,
        )

    def _on_connect(
        self,
        client: Any,
        _userdata: object,
        _flags: object,
        reason_code: object,
        _properties: object,
    ) -> None:
        if getattr(reason_code, "is_failure", reason_code != 0):
            self._set_error(f"MQTT connection refused: {reason_code}")
            LOGGER.error("MQTT connection refused: %s", reason_code)
            return
        with self._lock:
            self._connected = True
            self._last_error = None
        client.subscribe(self.settings.birth_topic, qos=1)
        LOGGER.info("Connected to MQTT broker")
        self._publish_all()

    def _on_connect_fail(self, _client: Any, _userdata: object) -> None:
        self._set_error("MQTT broker connection failed; retrying")
        LOGGER.warning("MQTT broker connection failed; retrying")

    def _on_disconnect(
        self,
        _client: Any,
        _userdata: object,
        _flags: object,
        reason_code: object,
        _properties: object,
    ) -> None:
        with self._lock:
            self._connected = False
            if getattr(reason_code, "is_failure", reason_code != 0):
                self._last_error = f"MQTT disconnected: {reason_code}"
        LOGGER.info("Disconnected from MQTT broker: %s", reason_code)

    def _on_message(self, _client: Any, _userdata: object, message: Any) -> None:
        if message.topic != self.settings.birth_topic:
            return
        if message.payload.decode("utf-8", errors="replace").strip() == "online":
            LOGGER.info("Home Assistant MQTT birth message received")
            self._publish_all()

    def _publish_all(self) -> None:
        self._publish(
            (
                MqttMessage(
                    availability_topic(self.settings),
                    "online",
                    retain=True,
                ),
                *discovery_messages(self.settings, self.language),
                *self._build_state_messages(),
            )
        )

    def _build_state_messages(self) -> tuple[MqttMessage, ...]:
        today = self._date_provider()
        return state_messages(
            self.settings,
            self.language,
            self._get_day(today),
            self._get_day(today + timedelta(days=1)),
        )

    def _get_day(self, target: date) -> PlanDay:
        week_start = target - timedelta(days=target.weekday())
        plan = self.plans.get_week(week_start)
        return next(day for day in plan.days if day.date == target)

    def _publish(self, messages: tuple[MqttMessage, ...]) -> None:
        client = self._client
        if client is None:
            return
        try:
            for message in messages:
                result = client.publish(
                    message.topic,
                    payload=message.payload,
                    qos=message.qos,
                    retain=message.retain,
                )
                if getattr(result, "rc", mqtt.MQTT_ERR_SUCCESS) != mqtt.MQTT_ERR_SUCCESS:
                    raise RuntimeError(
                        f"publish to {message.topic} failed with rc={result.rc}"
                    )
        except Exception as error:
            self._set_error(f"MQTT publish failed: {error}")
            LOGGER.exception("Could not publish Meal Planner MQTT state")

    def _is_connected(self) -> bool:
        with self._lock:
            return self._connected

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._connected = False
            self._last_error = message
