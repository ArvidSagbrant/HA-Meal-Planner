"""Runtime configuration loaded from Home Assistant add-on options."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .planner import PlannerSettings


SUPPORTED_LANGUAGES = {"en", "sv"}
SUPPORTED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    language: str = "en"
    log_level: str = "INFO"
    ingress_only: bool = False
    planner: PlannerSettings = field(default_factory=PlannerSettings)

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
        )
