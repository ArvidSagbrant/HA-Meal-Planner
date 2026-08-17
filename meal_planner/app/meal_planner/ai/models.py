"""Strict structured-output contracts shared by AI providers."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..catalog import ProteinSource
from ..schemas import NonEmptyName


class StrictAIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanAssignmentProposal(StrictAIModel):
    date: str = Field(min_length=10, max_length=10)
    meal_id: str = Field(min_length=1, max_length=64)

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class PlanRefinementProposal(StrictAIModel):
    assignments: list[PlanAssignmentProposal] = Field(min_length=7, max_length=7)
    summary: str = Field(max_length=500)


class MealSuggestion(StrictAIModel):
    name: NonEmptyName
    description: str = Field(max_length=1000)
    cooking_effort: int = Field(ge=1, le=5)
    meal_type: str = Field(min_length=1, max_length=80)
    protein_source: ProteinSource
    is_vegetarian: bool
    tags: list[str] = Field(max_length=8)


class MealSuggestions(StrictAIModel):
    suggestions: list[MealSuggestion] = Field(min_length=1, max_length=10)
