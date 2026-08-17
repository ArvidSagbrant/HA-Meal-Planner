"""Validated API contracts shared by routes and services."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from .catalog import ProteinSource


NonEmptyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class NutritionInfo(BaseModel):
    """Optional per-serving nutrition used by the planner and UI."""

    calories_kcal: float | None = Field(default=None, ge=0, le=10000)
    protein_g: float | None = Field(default=None, ge=0, le=1000)
    carbohydrates_g: float | None = Field(default=None, ge=0, le=1000)
    fat_g: float | None = Field(default=None, ge=0, le=1000)
    fiber_g: float | None = Field(default=None, ge=0, le=1000)


class MealBase(BaseModel):
    name: NonEmptyName
    description: str = Field(default="", max_length=4000)
    preference: int = Field(default=3, ge=1, le=5)
    cooking_effort: int = Field(default=3, ge=1, le=5)
    meal_type: str = Field(default="dinner", min_length=1, max_length=80)
    protein_source: ProteinSource = ProteinSource.OTHER
    is_vegetarian: bool = False
    tags: list[str] = Field(default_factory=list)
    nutrition: NutritionInfo = Field(default_factory=NutritionInfo)
    excluded: bool = False

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in value:
            clean = tag.strip()
            key = clean.casefold()
            if clean and key not in seen:
                normalized.append(clean)
                seen.add(key)
        return normalized


class MealCreate(MealBase):
    pass


class MealUpdate(BaseModel):
    name: NonEmptyName | None = None
    description: str | None = Field(default=None, max_length=4000)
    preference: int | None = Field(default=None, ge=1, le=5)
    cooking_effort: int | None = Field(default=None, ge=1, le=5)
    meal_type: str | None = Field(default=None, min_length=1, max_length=80)
    protein_source: ProteinSource | None = None
    is_vegetarian: bool | None = None
    tags: list[str] | None = None
    nutrition: NutritionInfo | None = None
    excluded: bool | None = None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return MealBase.normalize_tags(value)

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "MealUpdate":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class Meal(MealBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    image_path: str | None = None
    image_mime_type: str | None = None
    image_size_bytes: int | None = None
    created_at: datetime
    updated_at: datetime


class PlanAssignmentRequest(BaseModel):
    meal_id: str = Field(min_length=1, max_length=64)


class PlanCookedRequest(BaseModel):
    is_cooked: bool


class PlanDay(BaseModel):
    date: date
    meal: Meal | None
    assignment_type: str | None = None
    is_manual_override: bool = False
    is_cooked: bool = False


class WeeklyPlan(BaseModel):
    week_start: date
    week_end: date
    days: list[PlanDay]


class PlanningSettingsView(BaseModel):
    repeat_avoidance_weeks: int
    vegetarian_target: int
    preference_weight: float
    recency_weight: float
    effort_weight: float
    variety_weight: float
    nutrition_weight: float
    calorie_target_kcal: int
    max_consecutive_protein_source: int
    weekday_effort_target: int
    weekend_effort_target: int


class MqttSettingsView(BaseModel):
    enabled: bool
    mode: str
    broker: str | None
    tls: bool
    discovery_prefix: str
    topic_prefix: str


class MqttStatusView(BaseModel):
    enabled: bool
    connected: bool
    mode: str
    broker: str | None
    last_error: str | None


class AISettingsView(BaseModel):
    enabled: bool
    provider: str
    base_url: str | None
    model: str | None
    timeout_seconds: float
    temperature: float
    refinement_enabled: bool
    suggestions_enabled: bool


class AIStatusView(BaseModel):
    enabled: bool
    provider: str
    model: str | None
    refinement_enabled: bool
    suggestions_enabled: bool
    last_action: str | None
    last_error: str | None


class MealSuggestionRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=10)
    preferences: str = Field(default="", max_length=500)


class RuntimeSettings(BaseModel):
    language: str
    log_level: str
    protein_sources: list[ProteinSource]
    planning: PlanningSettingsView
    mqtt: MqttSettingsView
    ai: AISettingsView
