"""Weekly plan retrieval and manual assignment use cases."""

from __future__ import annotations

from datetime import date, timedelta

from ..errors import InvalidOperationError, NotFoundError
from ..repositories import MealRepository, PlanRepository
from ..schemas import Meal, PlanDay, WeeklyPlan


class PlanService:
    def __init__(self, plans: PlanRepository, meals: MealRepository) -> None:
        self.plans = plans
        self.meals = meals

    def get_week(self, week_start: date) -> WeeklyPlan:
        self._validate_week_start(week_start)
        days: list[PlanDay] = []
        for item in self.plans.get_days(week_start):
            meal_data = self.meals.get(item["meal_id"]) if item["meal_id"] else None
            days.append(
                PlanDay(
                    date=date.fromisoformat(item["meal_date"]),
                    meal=Meal.model_validate(meal_data) if meal_data else None,
                    assignment_type=item["assignment_type"] if item["meal_id"] else None,
                    is_manual_override=bool(item["is_manual_override"]),
                )
            )
        return WeeklyPlan(
            week_start=week_start,
            week_end=week_start + timedelta(days=6),
            days=days,
        )

    def assign_meal(self, week_start: date, meal_date: date, meal_id: str) -> WeeklyPlan:
        self._validate_day(week_start, meal_date)
        if self.meals.get(meal_id) is None:
            raise NotFoundError("Meal not found")
        self.plans.assign(week_start, meal_date, meal_id)
        return self.get_week(week_start)

    def clear_meal(self, week_start: date, meal_date: date) -> WeeklyPlan:
        self._validate_day(week_start, meal_date)
        self.plans.clear(week_start, meal_date)
        return self.get_week(week_start)

    @staticmethod
    def _validate_week_start(week_start: date) -> None:
        if week_start.weekday() != 0:
            raise InvalidOperationError("week_start must be a Monday")

    @classmethod
    def _validate_day(cls, week_start: date, meal_date: date) -> None:
        cls._validate_week_start(week_start)
        if not week_start <= meal_date <= week_start + timedelta(days=6):
            raise InvalidOperationError("meal_date must be within the requested week")

