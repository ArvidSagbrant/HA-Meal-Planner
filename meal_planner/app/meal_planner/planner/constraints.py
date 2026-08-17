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

    def can_assign(
        self,
        meal: MealCandidate,
        *,
        meal_date: date,
        week_start: date,
        assignments: dict[date, str],
        meals_by_id: dict[str, MealCandidate],
        history: PlanningHistory,
    ) -> bool:
        if not self.can_generate(
            meal,
            week_start=week_start,
            used_meal_ids=set(assignments.values()),
            history=history,
        ):
            return False
        maximum = self.settings.max_consecutive_protein_source
        source = meal.protein_source.casefold()
        run_length = 1
        for direction in (-1, 1):
            neighbor_date = meal_date + timedelta(days=direction)
            while assignments.get(neighbor_date):
                neighbor = meals_by_id[assignments[neighbor_date]]
                if neighbor.protein_source.casefold() != source:
                    break
                run_length += 1
                neighbor_date += timedelta(days=direction)
        return run_length <= maximum

    @staticmethod
    def validate_fixed_assignments(
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
