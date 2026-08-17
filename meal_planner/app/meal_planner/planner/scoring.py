"""Soft-preference scoring for otherwise valid meal candidates."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from .models import MealCandidate, PlannerSettings, PlanningHistory


class MealScorer:
    def __init__(self, settings: PlannerSettings) -> None:
        self.settings = settings

    def score(
        self,
        meal: MealCandidate,
        *,
        meal_date: date,
        assignments: dict[date, str],
        meals_by_id: dict[str, MealCandidate],
        history: PlanningHistory,
        previous_meal_id: str | None = None,
    ) -> float:
        score = self._preference_score(meal)
        score += self._recency_score(meal, meal_date, history)
        score += self._effort_score(meal, meal_date)
        score += self._variety_score(meal, meal_date, assignments, meals_by_id)
        score += self._vegetarian_score(meal, meal_date, assignments, meals_by_id)
        score += self._nutrition_score(meal, meal_date, assignments, meals_by_id)
        if previous_meal_id == meal.id:
            score -= 5.0 * max(self.settings.variety_weight, 0.5)
        return round(score, 6)

    def _preference_score(self, meal: MealCandidate) -> float:
        normalized = (meal.preference - 1) / 4
        return normalized * 4 * self.settings.preference_weight

    def _recency_score(
        self, meal: MealCandidate, meal_date: date, history: PlanningHistory
    ) -> float:
        last_used = history.last_used.get(meal.id)
        if last_used is None:
            return 4 * self.settings.recency_weight
        weeks_since = max((meal_date - last_used).days / 7, 0)
        return min(weeks_since / 3, 4) * self.settings.recency_weight

    def _effort_score(self, meal: MealCandidate, meal_date: date) -> float:
        target = (
            self.settings.weekend_effort_target
            if meal_date.weekday() >= 5
            else self.settings.weekday_effort_target
        )
        return -abs(meal.cooking_effort - target) * self.settings.effort_weight

    def _variety_score(
        self,
        meal: MealCandidate,
        meal_date: date,
        assignments: dict[date, str],
        meals_by_id: dict[str, MealCandidate],
    ) -> float:
        assigned_meals = [meals_by_id[meal_id] for meal_id in assignments.values()]
        protein_counts = Counter(item.protein_source.casefold() for item in assigned_meals)
        score = -protein_counts[meal.protein_source.casefold()] * self.settings.variety_weight

        for neighbor_date in (
            meal_date - timedelta(days=1),
            meal_date + timedelta(days=1),
        ):
            neighbor_id = assignments.get(neighbor_date)
            if not neighbor_id:
                continue
            neighbor = meals_by_id[neighbor_id]
            if neighbor.protein_source.casefold() == meal.protein_source.casefold():
                score -= 3 * self.settings.variety_weight
            shared_tags = {tag.casefold() for tag in meal.tags} & {
                tag.casefold() for tag in neighbor.tags
            }
            score -= len(shared_tags) * 0.5 * self.settings.variety_weight
        return score

    def _vegetarian_score(
        self,
        meal: MealCandidate,
        meal_date: date,
        assignments: dict[date, str],
        meals_by_id: dict[str, MealCandidate],
    ) -> float:
        target = self.settings.vegetarian_target
        vegetarian_count = sum(
            meals_by_id[meal_id].is_vegetarian for meal_id in assignments.values()
        )
        remaining_unassigned = 7 - len(assignments)
        needed = max(target - vegetarian_count, 0)
        if meal.is_vegetarian and vegetarian_count < target:
            return 3 * self.settings.variety_weight
        if not meal.is_vegetarian and remaining_unassigned <= needed:
            return -6 * self.settings.variety_weight
        if meal.is_vegetarian and vegetarian_count >= target:
            return -1.5 * self.settings.variety_weight
        return 0.0

    def _nutrition_score(
        self,
        meal: MealCandidate,
        meal_date: date,
        assignments: dict[date, str],
        meals_by_id: dict[str, MealCandidate],
    ) -> float:
        if not meal.nutrition or self.settings.nutrition_weight == 0:
            return 0.0
        nutrition = meal.nutrition
        score = 0.0
        calories = nutrition.get("calories_kcal")
        target = self.settings.calorie_target_kcal
        if calories is not None and target > 0:
            score += max(-2.0, 2.0 - abs(calories - target) / target * 4.0)
        protein = nutrition.get("protein_g")
        if protein is not None:
            score += min(protein / 25.0, 1.0)
        fiber = nutrition.get("fiber_g")
        if fiber is not None:
            score += min(fiber / 8.0, 1.0)

        for neighbor_date in (
            meal_date - timedelta(days=1),
            meal_date + timedelta(days=1),
        ):
            neighbor_id = assignments.get(neighbor_date)
            if not neighbor_id:
                continue
            neighbor = meals_by_id[neighbor_id].nutrition
            comparable = 0
            similar = 0
            for key, tolerance in (
                ("calories_kcal", 75.0),
                ("protein_g", 5.0),
                ("fiber_g", 2.0),
            ):
                if key not in nutrition or key not in neighbor:
                    continue
                comparable += 1
                similar += abs(nutrition[key] - neighbor[key]) <= tolerance
            if comparable >= 2 and similar == comparable:
                score -= 0.75
        return score * self.settings.nutrition_weight
