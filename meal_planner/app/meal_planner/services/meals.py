"""Meal management use cases."""

from __future__ import annotations

import sqlite3

from ..errors import ConflictError, NotFoundError
from ..repositories import MealRepository
from ..schemas import Meal, MealCreate, MealUpdate


class MealService:
    def __init__(self, repository: MealRepository) -> None:
        self.repository = repository

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
        return Meal.model_validate(item)

    def update_meal(self, meal_id: str, payload: MealUpdate) -> Meal:
        try:
            item = self.repository.update(meal_id, payload.model_dump(exclude_unset=True))
        except sqlite3.IntegrityError as error:
            raise ConflictError("A meal with this name already exists") from error
        if item is None:
            raise NotFoundError("Meal not found")
        return Meal.model_validate(item)

    def delete_meal(self, meal_id: str) -> None:
        if not self.repository.delete(meal_id):
            raise NotFoundError("Meal not found")

