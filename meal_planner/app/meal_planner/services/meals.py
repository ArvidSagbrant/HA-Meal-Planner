"""Meal management use cases."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from ..errors import ConflictError, NotFoundError
from ..repositories import MealRepository
from ..schemas import Meal, MealCreate, MealUpdate


class MealService:
    def __init__(
        self,
        repository: MealRepository,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self.repository = repository
        self._on_change = on_change or (lambda: None)

    def list_meals(self) -> list[Meal]:
        return [Meal.model_validate(item) for item in self.repository.list()]

    def get_meal(self, meal_id: str) -> Meal:
        item = self.repository.get(meal_id)
        if item is None:
            raise NotFoundError("Meal not found")
        return Meal.model_validate(item)

    def create_meal(self, payload: MealCreate) -> Meal:
        try:
            item = self.repository.create(payload.model_dump())
        except sqlite3.IntegrityError as error:
            raise ConflictError("A meal with this name already exists") from error
        meal = Meal.model_validate(item)
        self._on_change()
        return meal

    def update_meal(self, meal_id: str, payload: MealUpdate) -> Meal:
        try:
            item = self.repository.update(meal_id, payload.model_dump(exclude_unset=True))
        except sqlite3.IntegrityError as error:
            raise ConflictError("A meal with this name already exists") from error
        if item is None:
            raise NotFoundError("Meal not found")
        meal = Meal.model_validate(item)
        self._on_change()
        return meal

    def delete_meal(self, meal_id: str) -> None:
        if not self.repository.delete(meal_id):
            raise NotFoundError("Meal not found")
        self._on_change()
