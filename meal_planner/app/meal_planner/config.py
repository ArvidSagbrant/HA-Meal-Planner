"""Runtime configuration loaded from Home Assistant add-on options."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .planner import PlannerSettings


SUPPORTED_LANGUAGES = {"en", "sv"}
SUPPORTED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
SUPPORTED_MQTT_MODES = {"auto", "external", "disabled"}


@dataclass(frozen=True, slots=True)
class MqttSettings:
    enabled: bool = False
    mode: str = "disabled"
    host: str = ""
    port: int = 1883
    username: str = ""
    password: str = field(default="", repr=False)
    tls: bool = False
    discovery_prefix: str = "homeassistant"
    topic_prefix: str = "meal_planner"
    birth_topic: str = "homeassistant/status"

    def __post_init__(self) -> None:
        if self.mode not in SUPPORTED_MQTT_MODES:
            raise ValueError(f"Unsupported MQTT mode: {self.mode}")
        if self.enabled and not self.host.strip():
            raise ValueError("MQTT host is required when MQTT is enabled")
        if not 1 <= self.port <= 65535:
            raise ValueError("MQTT port must be between 1 and 65535")
        for name in ("discovery_prefix", "topic_prefix", "birth_topic"):
            raw_value = getattr(self, name)
            value = raw_value.strip().strip("/")
            if (
                not value
                or value != raw_value
                or any(character in value for character in ("#", "+"))
            ):
                raise ValueError(f"Invalid MQTT topic in {name}")


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    language: str = "en"
    log_level: str = "INFO"
    ingress_only: bool = False
    planner: PlannerSettings = field(default_factory=PlannerSettings)
    mqtt: MqttSettings = field(default_factory=MqttSettings)

    @property
    def database_path(self) -> Path:
        return self.data_dir / "meal_planner.db"

    @classmethod
    def from_environment(cls) -> "Settings":
        language = os.getenv("MEAL_PLANNER_LANGUAGE", "en").lower()
        log_level = os.getenv("MEAL_PLANNER_LOG_LEVEL", "INFO").upper()

        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        if log_level not in SUPPORTED_LOG_LEVELS:
            raise ValueError(f"Unsupported log level: {log_level}")
        mqtt_mode = os.getenv("MEAL_PLANNER_MQTT_MODE", "disabled").lower()
        if mqtt_mode not in SUPPORTED_MQTT_MODES:
            raise ValueError(f"Unsupported MQTT mode: {mqtt_mode}")

        return cls(
            data_dir=Path(os.getenv("MEAL_PLANNER_DATA_DIR", "/data")),
            language=language,
            log_level=log_level,
            ingress_only=os.getenv("MEAL_PLANNER_INGRESS_ONLY", "false").lower()
            in {"1", "true", "yes"},
            planner=PlannerSettings(
                repeat_avoidance_weeks=int(
                    os.getenv("MEAL_PLANNER_REPEAT_AVOIDANCE_WEEKS", "2")
                ),
                vegetarian_target=int(
                    os.getenv("MEAL_PLANNER_VEGETARIAN_TARGET", "2")
                ),
                preference_weight=float(
                    os.getenv("MEAL_PLANNER_PREFERENCE_WEIGHT", "1.0")
                ),
                recency_weight=float(
                    os.getenv("MEAL_PLANNER_RECENCY_WEIGHT", "1.0")
                ),
                effort_weight=float(
                    os.getenv("MEAL_PLANNER_EFFORT_WEIGHT", "0.6")
                ),
                variety_weight=float(
                    os.getenv("MEAL_PLANNER_VARIETY_WEIGHT", "1.0")
                ),
                weekday_effort_target=int(
                    os.getenv("MEAL_PLANNER_WEEKDAY_EFFORT_TARGET", "2")
                ),
                weekend_effort_target=int(
                    os.getenv("MEAL_PLANNER_WEEKEND_EFFORT_TARGET", "4")
                ),
            ),
            mqtt=MqttSettings(
                enabled=os.getenv("MEAL_PLANNER_MQTT_ENABLED", "false").lower()
                in {"1", "true", "yes"},
                mode=mqtt_mode,
                host=os.getenv("MEAL_PLANNER_MQTT_HOST", ""),
                port=int(os.getenv("MEAL_PLANNER_MQTT_PORT", "1883")),
                username=os.getenv("MEAL_PLANNER_MQTT_USERNAME", ""),
                password=os.getenv("MEAL_PLANNER_MQTT_PASSWORD", ""),
                tls=os.getenv("MEAL_PLANNER_MQTT_TLS", "false").lower()
                in {"1", "true", "yes"},
                discovery_prefix=os.getenv(
                    "MEAL_PLANNER_MQTT_DISCOVERY_PREFIX", "homeassistant"
                ),
                topic_prefix=os.getenv(
                    "MEAL_PLANNER_MQTT_TOPIC_PREFIX", "meal_planner"
                ),
                birth_topic=os.getenv(
                    "MEAL_PLANNER_MQTT_BIRTH_TOPIC", "homeassistant/status"
                ),
            ),
        )
