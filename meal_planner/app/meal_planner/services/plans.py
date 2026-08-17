"""Weekly plan retrieval and manual assignment use cases."""

from __future__ import annotations

from datetime import date, timedelta

from ..errors import (
    DuplicateAssignmentError,
    InvalidOperationError,
    NotFoundError,
    PlanningError,
)
from ..planner import (
    DeterministicPlanner,
    MealCandidate,
    PlanSlot,
    PlanningFailure,
    PlanningHistory,
)
from ..repositories import MealRepository, PlanRepository
from ..schemas import Meal, PlanDay, WeeklyPlan


class PlanService:
    def __init__(
        self,
        plans: PlanRepository,
        meals: MealRepository,
        planner: DeterministicPlanner,
    ) -> None:
        self.plans = plans
        self.meals = meals
        self.planner = planner

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
        duplicate_day = next(
            (
                item["meal_date"]
                for item in self.plans.get_days(week_start)
                if item["meal_id"] == meal_id
                and item["meal_date"] != meal_date.isoformat()
            ),
            None,
        )
        if duplicate_day:
            raise DuplicateAssignmentError(
                "The same meal cannot be assigned twice in one week"
            )
        self.plans.assign(week_start, meal_date, meal_id)
        return self.get_week(week_start)

    def clear_meal(self, week_start: date, meal_date: date) -> WeeklyPlan:
        self._validate_day(week_start, meal_date)
        self.plans.clear(week_start, meal_date)
        return self.get_week(week_start)

    def generate_week(self, week_start: date) -> WeeklyPlan:
        self._validate_week_start(week_start)
        meal_data = self.meals.list()
        day_data = self.plans.get_days(week_start)
        try:
            result = self.planner.generate_week(
                week_start=week_start,
                meals=self._meal_candidates(meal_data),
                slots=self._plan_slots(day_data),
                history=PlanningHistory(self.plans.get_last_used(week_start)),
                previous_assignments={
                    date.fromisoformat(item["meal_date"]): item["meal_id"]
                    for item in day_data
                    if item["meal_id"] and not item["is_manual_override"]
                },
            )
        except PlanningFailure as error:
            raise PlanningError(str(error)) from error
        self.plans.replace_generated(week_start, result.assignments)
        return self.get_week(week_start)

    def regenerate_day(self, week_start: date, meal_date: date) -> WeeklyPlan:
        self._validate_day(week_start, meal_date)
        meal_data = self.meals.list()
        day_data = self.plans.get_days(week_start)
        try:
            meal_id, _score = self.planner.regenerate_day(
                week_start=week_start,
                meal_date=meal_date,
                meals=self._meal_candidates(meal_data),
                slots=self._plan_slots(day_data),
                history=PlanningHistory(self.plans.get_last_used(week_start)),
            )
        except PlanningFailure as error:
            raise PlanningError(str(error)) from error
        self.plans.assign_generated(week_start, meal_date, meal_id)
        return self.get_week(week_start)

    @staticmethod
    def _meal_candidates(items: list[dict]) -> list[MealCandidate]:
        return [
            MealCandidate(
                id=item["id"],
                name=item["name"],
                preference=item["preference"],
                cooking_effort=item["cooking_effort"],
                protein_source=item["protein_source"],
                tags=tuple(item["tags"]),
                excluded=item["excluded"],
            )
            for item in items
        ]

    @staticmethod
    def _plan_slots(items: list[dict]) -> list[PlanSlot]:
        return [
            PlanSlot(
                date=date.fromisoformat(item["meal_date"]),
                meal_id=item["meal_id"],
                is_manual_override=bool(item["is_manual_override"]),
            )
            for item in items
        ]

    @staticmethod
    def _validate_week_start(week_start: date) -> None:
        if week_start.weekday() != 0:
            raise InvalidOperationError("week_start must be a Monday")

    @classmethod
    def _validate_day(cls, week_start: date, meal_date: date) -> None:
        cls._validate_week_start(week_start)
        if not week_start <= meal_date <= week_start + timedelta(days=6):
            raise InvalidOperationError("meal_date must be within the requested week")
