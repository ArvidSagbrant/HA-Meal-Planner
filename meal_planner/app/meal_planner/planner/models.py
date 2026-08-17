"""Provider- and persistence-independent planner models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


class PlanningFailure(Exception):
    """Raised when no plan can satisfy all hard constraints."""


@dataclass(frozen=True, slots=True)
class PlannerSettings:
    repeat_avoidance_weeks: int = 2
    vegetarian_target: int = 2
    preference_weight: float = 1.0
    recency_weight: float = 1.0
    effort_weight: float = 0.6
    variety_weight: float = 1.0
    weekday_effort_target: int = 2
    weekend_effort_target: int = 4

    def __post_init__(self) -> None:
        if not 0 <= self.repeat_avoidance_weeks <= 52:
            raise ValueError("repeat_avoidance_weeks must be between 0 and 52")
        if not 0 <= self.vegetarian_target <= 7:
            raise ValueError("vegetarian_target must be between 0 and 7")
        for name in (
            "preference_weight",
            "recency_weight",
            "effort_weight",
            "variety_weight",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")
        if not 1 <= self.weekday_effort_target <= 5:
            raise ValueError("weekday_effort_target must be between 1 and 5")
        if not 1 <= self.weekend_effort_target <= 5:
            raise ValueError("weekend_effort_target must be between 1 and 5")


@dataclass(frozen=True, slots=True)
class MealCandidate:
    id: str
    name: str
    preference: int
    cooking_effort: int
    protein_source: str
    is_vegetarian: bool = False
    tags: tuple[str, ...] = ()
    excluded: bool = False


@dataclass(frozen=True, slots=True)
class PlanSlot:
    date: date
    meal_id: str | None = None
    is_manual_override: bool = False
    is_cooked: bool = False


@dataclass(frozen=True, slots=True)
class PlanningHistory:
    last_used: dict[str, date] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PlanningResult:
    assignments: dict[date, str]
    scores: dict[date, float]
