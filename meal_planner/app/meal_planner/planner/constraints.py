"""Hard constraints for generated weekly plans."""

from __future__ import annotations

from datetime import date, timedelta

from .models import MealCandidate, PlannerSettings, PlanningFailure, PlanningHistory


class HardConstraints:
    def __init__(self, settings: PlannerSettings) -> None:
        self.settings = settings

    def can_generate(
        self,
        meal: MealCandidate,
        *,
        week_start: date,
        used_meal_ids: set[str],
        history: PlanningHistory,
    ) -> bool:
        if meal.excluded or meal.id in used_meal_ids:
            return False
        if self.settings.repeat_avoidance_weeks == 0:
            return True
        last_used = history.last_used.get(meal.id)
        cutoff = week_start - timedelta(weeks=self.settings.repeat_avoidance_weeks)
        return last_used is None or last_used < cutoff or last_used >= week_start

    @staticmethod
    def validate_manual_assignments(
        assignments: dict[date, str], meals_by_id: dict[str, MealCandidate]
    ) -> None:
        unknown_ids = sorted(set(assignments.values()) - meals_by_id.keys())
        if unknown_ids:
            raise PlanningFailure("The plan contains a meal that no longer exists")
        if len(assignments.values()) != len(set(assignments.values())):
            raise PlanningFailure("The same meal cannot be used more than once in a week")
    @staticmethod
    def validate_complete_week(
        assignments: dict[date, str],
        meals_by_id: dict[str, MealCandidate],
        expected_dates: set[date],
    ) -> None:
        if set(assignments) != expected_dates:
            raise PlanningFailure("Every day in the week must have a meal")
        unknown_ids = set(assignments.values()) - meals_by_id.keys()
        if unknown_ids:
            raise PlanningFailure("The generated plan references an unknown meal")
        if len(assignments.values()) != len(set(assignments.values())):
            raise PlanningFailure("The same meal cannot be used more than once in a week")
