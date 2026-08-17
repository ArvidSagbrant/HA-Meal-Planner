"""AI use cases with deterministic validation and graceful fallback."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from threading import Lock

from ..catalog import PROTEIN_SOURCES
from ..config import AISettings
from ..planner import (
    DeterministicPlanner,
    MealCandidate,
    PlanSlot,
    PlanningFailure,
    PlanningHistory,
    PlanningResult,
)
from ..repositories import MealRepository
from .models import MealSuggestion, MealSuggestions, PlanRefinementProposal
from .providers import AIProvider, AIProviderError


LOGGER = logging.getLogger(__name__)
MAX_CANDIDATES = 200


@dataclass(frozen=True, slots=True)
class AIServiceStatus:
    enabled: bool
    provider: str
    model: str | None
    refinement_enabled: bool
    suggestions_enabled: bool
    last_action: str | None
    last_error: str | None


class AIService:
    def __init__(
        self,
        settings: AISettings,
        provider: AIProvider,
        planner: DeterministicPlanner,
        meals: MealRepository,
        language: str,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.planner = planner
        self.meals = meals
        self.language = language
        self._last_action: str | None = None
        self._last_error: str | None = None
        self._lock = Lock()

    def refine_plan(
        self,
        *,
        week_start: date,
        deterministic: PlanningResult,
        meals: list[MealCandidate],
        slots: list[PlanSlot],
        history: PlanningHistory,
    ) -> PlanningResult:
        if not self.settings.enabled or not self.settings.refinement_enabled:
            return deterministic
        try:
            proposal = self.provider.complete_structured(
                system_prompt=self._plan_system_prompt(),
                user_prompt=self._plan_user_prompt(
                    week_start,
                    deterministic,
                    meals,
                    slots,
                ),
                response_model=PlanRefinementProposal,
            )
            assignments = {
                date.fromisoformat(assignment.date): assignment.meal_id
                for assignment in proposal.assignments
            }
            self.planner.validate_plan(
                week_start=week_start,
                assignments=assignments,
                meals=meals,
                slots=slots,
                history=history,
            )
        except (AIProviderError, PlanningFailure, ValueError) as error:
            self._record_error("plan_refinement", str(error))
            LOGGER.warning(
                "AI plan refinement was rejected; using deterministic plan: %s",
                error,
            )
            return deterministic

        self._record_success("plan_refinement")
        LOGGER.info("AI plan refinement passed deterministic validation")
        return PlanningResult(assignments=assignments, scores=deterministic.scores)

    def suggest_meals(
        self,
        *,
        count: int,
        preferences: str,
    ) -> list[MealSuggestion]:
        if not self.settings.enabled:
            raise AIProviderError("No AI provider is configured")
        if not self.settings.suggestions_enabled:
            raise AIProviderError("AI meal suggestions are disabled")
        existing = self.meals.list()
        try:
            response = self.provider.complete_structured(
                system_prompt=self._suggestion_system_prompt(),
                user_prompt=self._suggestion_user_prompt(
                    existing,
                    count,
                    preferences,
                ),
                response_model=MealSuggestions,
            )
            existing_names = {item["name"].casefold() for item in existing}
            seen = set(existing_names)
            suggestions = []
            for suggestion in response.suggestions:
                name = suggestion.name.casefold()
                if name in seen:
                    continue
                seen.add(name)
                suggestions.append(suggestion)
                if len(suggestions) == count:
                    break
            if not suggestions:
                raise AIProviderError("AI returned no new meal suggestions")
        except AIProviderError as error:
            self._record_error("meal_suggestions", str(error))
            raise

        self._record_success("meal_suggestions")
        return suggestions

    def status(self) -> AIServiceStatus:
        with self._lock:
            return AIServiceStatus(
                enabled=self.settings.enabled,
                provider=self.settings.provider,
                model=self.settings.model if self.settings.enabled else None,
                refinement_enabled=(
                    self.settings.enabled and self.settings.refinement_enabled
                ),
                suggestions_enabled=(
                    self.settings.enabled and self.settings.suggestions_enabled
                ),
                last_action=self._last_action,
                last_error=self._last_error,
            )

    def close(self) -> None:
        self.provider.close()

    def _plan_system_prompt(self) -> str:
        return (
            "You refine a valid weekly meal plan. Return exactly one assignment for "
            "each supplied date. Use only candidate meal IDs. Preserve every fixed "
            "assignment. Improve subjective variety without inventing meals."
        )

    def _plan_user_prompt(
        self,
        week_start: date,
        deterministic: PlanningResult,
        meals: list[MealCandidate],
        slots: list[PlanSlot],
    ) -> str:
        fixed = {
            slot.date.isoformat(): slot.meal_id
            for slot in slots
            if (slot.is_manual_override or slot.is_cooked) and slot.meal_id
        }
        selected_ids = set(deterministic.assignments.values())
        selected = [meal for meal in meals if meal.id in selected_ids]
        remaining = sorted(
            (meal for meal in meals if meal.id not in selected_ids and not meal.excluded),
            key=lambda meal: (-meal.preference, meal.name.casefold(), meal.id),
        )
        candidates = (selected + remaining)[:MAX_CANDIDATES]
        payload = {
            "language": self.language,
            "week_start": week_start.isoformat(),
            "goals": [
                "varied protein sources",
                "spread vegetarian meals",
                "avoid consecutive high-effort meals",
                "prefer highly rated meals",
                "maintain nutritional variety when values are available",
            ],
            "fixed_assignments": fixed,
            "current_plan": {
                day.isoformat(): meal_id
                for day, meal_id in sorted(deterministic.assignments.items())
            },
            "candidates": [
                {
                    "id": meal.id,
                    "name": meal.name,
                    "preference": meal.preference,
                    "cooking_effort": meal.cooking_effort,
                    "protein_source": meal.protein_source,
                    "is_vegetarian": meal.is_vegetarian,
                    "tags": list(meal.tags),
                    "nutrition": meal.nutrition,
                }
                for meal in candidates
            ],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _suggestion_system_prompt(self) -> str:
        return (
            "Suggest practical dinner meals that are distinct from the existing "
            "database. Use only the supplied protein_source enum values. Do not "
            "claim exact nutrition values. Return all text in the requested language."
        )

    def _suggestion_user_prompt(
        self,
        existing: list[dict],
        count: int,
        preferences: str,
    ) -> str:
        payload = {
            "language": self.language,
            "requested_count": count,
            "preferences": preferences,
            "allowed_protein_sources": list(PROTEIN_SOURCES),
            "existing_meals": [
                {
                    "name": item["name"],
                    "protein_source": item["protein_source"],
                    "is_vegetarian": item["is_vegetarian"],
                    "tags": item["tags"],
                }
                for item in existing[:MAX_CANDIDATES]
            ],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _record_success(self, action: str) -> None:
        with self._lock:
            self._last_action = action
            self._last_error = None

    def _record_error(self, action: str, message: str) -> None:
        with self._lock:
            self._last_action = action
            self._last_error = message
