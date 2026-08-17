"""Meal management use cases."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from ..errors import ConflictError, ImageValidationError, NotFoundError
from ..images import InvalidImageError, MealImageStore
from ..repositories import MealRepository
from ..schemas import Meal, MealCreate, MealUpdate


class MealService:
    def __init__(
        self,
        repository: MealRepository,
        images: MealImageStore,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self.repository = repository
        self.images = images
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
        item = self.repository.get(meal_id)
        if item is None:
            raise NotFoundError("Meal not found")
        if not self.repository.delete(meal_id):
            raise NotFoundError("Meal not found")
        self.images.delete(item["image_path"])
        self._on_change()

    def save_image(self, meal_id: str, data: bytes) -> Meal:
        item = self.repository.get(meal_id)
        if item is None:
            raise NotFoundError("Meal not found")
        try:
            stored = self.images.save(meal_id, data)
        except InvalidImageError as error:
            raise ImageValidationError(str(error)) from error
        try:
            updated = self.repository.update(
                meal_id,
                {
                    "image_path": stored.filename,
                    "image_mime_type": stored.media_type,
                    "image_size_bytes": stored.size_bytes,
                },
            )
        except Exception:
            self.images.delete(stored.filename)
            raise
        if updated is None:
            self.images.delete(stored.filename)
            raise NotFoundError("Meal not found")
        if item["image_path"] != stored.filename:
            self.images.delete(item["image_path"])
        self._on_change()
        return Meal.model_validate(updated)

    def get_image(self, meal_id: str) -> tuple[Path, str]:
        item = self.repository.get(meal_id)
        if item is None:
            raise NotFoundError("Meal not found")
        if not item["image_path"] or not item["image_mime_type"]:
            raise NotFoundError("Meal image not found")
        try:
            path = self.images.path(item["image_path"])
        except InvalidImageError as error:
            raise NotFoundError("Meal image not found") from error
        if not path.is_file():
            raise NotFoundError("Meal image not found")
        return path, item["image_mime_type"]

    def delete_image(self, meal_id: str) -> Meal:
        item = self.repository.get(meal_id)
        if item is None:
            raise NotFoundError("Meal not found")
        updated = self.repository.update(
            meal_id,
            {
                "image_path": None,
                "image_mime_type": None,
                "image_size_bytes": None,
            },
        )
        if updated is None:
            raise NotFoundError("Meal not found")
        self.images.delete(item["image_path"])
        self._on_change()
        return Meal.model_validate(updated)

    def prune_images(self) -> None:
        self.images.prune(
            {
                item["image_path"]
                for item in self.repository.list()
                if item["image_path"]
            }
        )
