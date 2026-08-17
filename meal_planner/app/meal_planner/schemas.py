"""Validated API contracts shared by routes and services."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


NonEmptyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class MealBase(BaseModel):
    name: NonEmptyName
    description: str = Field(default="", max_length=4000)
    preference: int = Field(default=3, ge=1, le=5)
    cooking_effort: int = Field(default=3, ge=1, le=5)
    image_path: str | None = Field(default=None, max_length=500)
    meal_type: str = Field(default="dinner", min_length=1, max_length=80)
    protein_source: str = Field(default="other", min_length=1, max_length=80)
    tags: list[str] = Field(default_factory=list)
    nutrition: dict[str, float] = Field(default_factory=dict)
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
    image_path: str | None = Field(default=None, max_length=500)
    meal_type: str | None = Field(default=None, min_length=1, max_length=80)
    protein_source: str | None = Field(default=None, min_length=1, max_length=80)
    tags: list[str] | None = None
    nutrition: dict[str, float] | None = None
    excluded: bool | None = None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return MealBase.normalize_tags(value)

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "MealUpdate":
        nullable_fields = {"image_path"}
        for field_name in self.model_fields_set - nullable_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class Meal(MealBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class PlanAssignmentRequest(BaseModel):
    meal_id: str = Field(min_length=1, max_length=64)


class PlanDay(BaseModel):
    date: date
    meal: Meal | None
    assignment_type: str | None = None
    is_manual_override: bool = False


class WeeklyPlan(BaseModel):
    week_start: date
    week_end: date
    days: list[PlanDay]


class RuntimeSettings(BaseModel):
    language: str
    log_level: str
