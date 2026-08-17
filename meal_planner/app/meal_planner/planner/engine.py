"""Deterministic constraint-and-score based meal planning engine."""

from __future__ import annotations

from datetime import date, timedelta

from .constraints import HardConstraints
from .models import (
    MealCandidate,
    PlanSlot,
    PlannerSettings,
    PlanningFailure,
    PlanningHistory,
    PlanningResult,
)
from .scoring import MealScorer


class DeterministicPlanner:
    def __init__(self, settings: PlannerSettings) -> None:
        self.settings = settings
        self.constraints = HardConstraints(settings)
        self.scorer = MealScorer(settings)

    def generate_week(
        self,
        *,
        week_start: date,
        meals: list[MealCandidate],
        slots: list[PlanSlot],
        history: PlanningHistory,
        previous_assignments: dict[date, str] | None = None,
    ) -> PlanningResult:
        expected_dates = self._expected_dates(week_start)
        self._validate_slots(slots, expected_dates)
        meals_by_id = {meal.id: meal for meal in meals}
        fixed_assignments = {
            slot.date: slot.meal_id
            for slot in slots
            if (slot.is_manual_override or slot.is_cooked) and slot.meal_id is not None
        }
        self.constraints.validate_fixed_assignments(fixed_assignments, meals_by_id)

        assignments = dict(fixed_assignments)
        used_ids = set(assignments.values())
        open_dates = sorted(expected_dates - assignments.keys())
        eligible_count = sum(
            self.constraints.can_generate(
                meal,
                week_start=week_start,
                used_meal_ids=used_ids,
                history=history,
            )
            for meal in meals
        )
        if eligible_count < len(open_dates):
            raise PlanningFailure(
                "Not enough eligible meals to fill the week without repeats"
            )

        scores: dict[date, float] = {}
        previous_assignments = previous_assignments or {}
        if not self._fill_open_dates(
            open_dates=open_dates,
            index=0,
            meals=meals,
            week_start=week_start,
            assignments=assignments,
            meals_by_id=meals_by_id,
            history=history,
            previous_assignments=previous_assignments,
            scores=scores,
            dead_states=set(),
        ):
            raise PlanningFailure("No complete plan satisfies the hard constraints")

        self.constraints.validate_complete_week(assignments, meals_by_id, expected_dates)
        return PlanningResult(assignments=assignments, scores=scores)

    def regenerate_day(
        self,
        *,
        week_start: date,
        meal_date: date,
        meals: list[MealCandidate],
        slots: list[PlanSlot],
        history: PlanningHistory,
    ) -> tuple[str, float]:
        expected_dates = self._expected_dates(week_start)
        self._validate_slots(slots, expected_dates)
        if meal_date not in expected_dates:
            raise PlanningFailure("The requested day is outside the selected week")

        target_slot = next(slot for slot in slots if slot.date == meal_date)
        if target_slot.is_cooked:
            raise PlanningFailure("A cooked day cannot be regenerated")
        if target_slot.is_manual_override:
            raise PlanningFailure("Clear the manual override before regenerating this day")

        meals_by_id = {meal.id: meal for meal in meals}
        assignments = {
            slot.date: slot.meal_id
            for slot in slots
            if slot.date != meal_date and slot.meal_id is not None
        }
        self.constraints.validate_fixed_assignments(assignments, meals_by_id)
        ranked = self._rank_candidates(
            meals=meals,
            meal_date=meal_date,
            week_start=week_start,
            assignments=assignments,
            meals_by_id=meals_by_id,
            history=history,
            previous_meal_id=target_slot.meal_id,
            excluded_meal_id=target_slot.meal_id,
        )
        if not ranked:
            raise PlanningFailure("No different meal satisfies the hard constraints")
        score, selected = ranked[0]
        return selected.id, score

    def validate_plan(
        self,
        *,
        week_start: date,
        assignments: dict[date, str],
        meals: list[MealCandidate],
        slots: list[PlanSlot],
        history: PlanningHistory,
    ) -> None:
        """Validate a complete external proposal against every hard constraint."""
        expected_dates = self._expected_dates(week_start)
        self._validate_slots(slots, expected_dates)
        meals_by_id = {meal.id: meal for meal in meals}
        self.constraints.validate_complete_week(
            assignments,
            meals_by_id,
            expected_dates,
        )
        fixed_assignments = {
            slot.date: slot.meal_id
            for slot in slots
            if (slot.is_manual_override or slot.is_cooked) and slot.meal_id is not None
        }
        if any(assignments.get(day) != meal_id for day, meal_id in fixed_assignments.items()):
            raise PlanningFailure("The proposed plan changed a fixed assignment")

        accepted_assignments = dict(fixed_assignments)
        for meal_date in sorted(expected_dates - fixed_assignments.keys()):
            meal = meals_by_id[assignments[meal_date]]
            if not self.constraints.can_assign(
                meal,
                meal_date=meal_date,
                week_start=week_start,
                assignments=accepted_assignments,
                meals_by_id=meals_by_id,
                history=history,
            ):
                raise PlanningFailure("The proposed plan violates a hard constraint")
            accepted_assignments[meal_date] = meal.id

    def _rank_candidates(
        self,
        *,
        meals: list[MealCandidate],
        meal_date: date,
        week_start: date,
        assignments: dict[date, str],
        meals_by_id: dict[str, MealCandidate],
        history: PlanningHistory,
        previous_meal_id: str | None,
        excluded_meal_id: str | None = None,
    ) -> list[tuple[float, MealCandidate]]:
        ranked = []
        for meal in meals:
            if meal.id == excluded_meal_id:
                continue
            if not self.constraints.can_assign(
                meal,
                meal_date=meal_date,
                week_start=week_start,
                assignments=assignments,
                meals_by_id=meals_by_id,
                history=history,
            ):
                continue
            score = self.scorer.score(
                meal,
                meal_date=meal_date,
                assignments=assignments,
                meals_by_id=meals_by_id,
                history=history,
                previous_meal_id=previous_meal_id,
            )
            ranked.append((score, meal))
        ranked.sort(key=lambda item: (-item[0], item[1].name.casefold(), item[1].id))
        return ranked

    def _fill_open_dates(
        self,
        *,
        open_dates: list[date],
        index: int,
        meals: list[MealCandidate],
        week_start: date,
        assignments: dict[date, str],
        meals_by_id: dict[str, MealCandidate],
        history: PlanningHistory,
        previous_assignments: dict[date, str],
        scores: dict[date, float],
        dead_states: set[tuple[tuple[str, str], ...]],
    ) -> bool:
        if index == len(open_dates):
            return True
        state_key = tuple(
            (
                assigned_date.isoformat(),
                meal_id,
            )
            for assigned_date, meal_id in sorted(assignments.items())
        )
        if state_key in dead_states:
            return False
        meal_date = open_dates[index]
        ranked = self._rank_candidates(
            meals=meals,
            meal_date=meal_date,
            week_start=week_start,
            assignments=assignments,
            meals_by_id=meals_by_id,
            history=history,
            previous_meal_id=previous_assignments.get(meal_date),
        )
        for score, selected in ranked:
            assignments[meal_date] = selected.id
            scores[meal_date] = score
            if self._fill_open_dates(
                open_dates=open_dates,
                index=index + 1,
                meals=meals,
                week_start=week_start,
                assignments=assignments,
                meals_by_id=meals_by_id,
                history=history,
                previous_assignments=previous_assignments,
                scores=scores,
                dead_states=dead_states,
            ):
                return True
            assignments.pop(meal_date)
            scores.pop(meal_date)
        dead_states.add(state_key)
        return False

    @staticmethod
    def _expected_dates(week_start: date) -> set[date]:
        if week_start.weekday() != 0:
            raise PlanningFailure("week_start must be a Monday")
        return {week_start + timedelta(days=offset) for offset in range(7)}

    @staticmethod
    def _validate_slots(slots: list[PlanSlot], expected_dates: set[date]) -> None:
        if len(slots) != 7 or {slot.date for slot in slots} != expected_dates:
            raise PlanningFailure("A weekly plan must contain Monday through Sunday")
