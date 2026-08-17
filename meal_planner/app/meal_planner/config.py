"""Runtime configuration loaded from Home Assistant add-on options."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from .planner import PlannerSettings


SUPPORTED_LANGUAGES = {"en", "sv"}
SUPPORTED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
SUPPORTED_MQTT_MODES = {"auto", "external", "disabled"}
SUPPORTED_AI_PROVIDERS = {"disabled", "openai", "llamacpp"}


@dataclass(frozen=True, slots=True)
class AISettings:
    provider: str = "disabled"
    base_url: str = ""
    api_key: str = field(default="", repr=False)
    model: str = "gpt-5-mini"
    timeout_seconds: float = 30.0
    temperature: float = 0.2
    refinement_enabled: bool = True
    suggestions_enabled: bool = True

    def __post_init__(self) -> None:
        if self.provider not in SUPPORTED_AI_PROVIDERS:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
        if self.provider != "disabled" and not self.base_url.strip():
            raise ValueError("AI base URL is required when AI is enabled")
        if self.provider != "disabled":
            parsed_url = urlsplit(self.base_url)
            if (
                self.base_url != self.base_url.strip()
                or parsed_url.scheme not in {"http", "https"}
                or not parsed_url.netloc
            ):
                raise ValueError("AI base URL must be a valid HTTP(S) URL")
        if self.provider != "disabled" and not self.model.strip():
            raise ValueError("AI model is required when AI is enabled")
        if not 1 <= self.timeout_seconds <= 300:
            raise ValueError("AI timeout must be between 1 and 300 seconds")
        if not 0 <= self.temperature <= 2:
            raise ValueError("AI temperature must be between 0 and 2")

    @property
    def enabled(self) -> bool:
        return self.provider != "disabled"


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
    ai: AISettings = field(default_factory=AISettings)

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
        ai_provider = os.getenv("MEAL_PLANNER_AI_PROVIDER", "disabled").lower()
        if ai_provider not in SUPPORTED_AI_PROVIDERS:
            raise ValueError(f"Unsupported AI provider: {ai_provider}")
        default_ai_url = {
            "openai": "https://api.openai.com/v1",
            "llamacpp": "http://localhost:8080/v1",
        }.get(ai_provider, "")

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
                nutrition_weight=float(
                    os.getenv("MEAL_PLANNER_NUTRITION_WEIGHT", "0.5")
                ),
                calorie_target_kcal=int(
                    os.getenv("MEAL_PLANNER_CALORIE_TARGET_KCAL", "600")
                ),
                max_consecutive_protein_source=int(
                    os.getenv(
                        "MEAL_PLANNER_MAX_CONSECUTIVE_PROTEIN_SOURCE",
                        "7",
                    )
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
            ai=AISettings(
                provider=ai_provider,
                base_url=os.getenv("MEAL_PLANNER_AI_BASE_URL", default_ai_url),
                api_key=os.getenv("MEAL_PLANNER_AI_API_KEY", ""),
                model=os.getenv("MEAL_PLANNER_AI_MODEL", "gpt-5-mini"),
                timeout_seconds=float(
                    os.getenv("MEAL_PLANNER_AI_TIMEOUT_SECONDS", "30")
                ),
                temperature=float(os.getenv("MEAL_PLANNER_AI_TEMPERATURE", "0.2")),
                refinement_enabled=os.getenv(
                    "MEAL_PLANNER_AI_REFINEMENT_ENABLED", "true"
                ).lower()
                in {"1", "true", "yes"},
                suggestions_enabled=os.getenv(
                    "MEAL_PLANNER_AI_SUGGESTIONS_ENABLED", "true"
                ).lower()
                in {"1", "true", "yes"},
            ),
        )
