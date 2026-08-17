"""Meal CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from ...schemas import Meal, MealCreate, MealUpdate
from ...services.meals import MealService
from ..dependencies import get_meal_service


router = APIRouter(prefix="/meals", tags=["meals"])
MealServiceDependency = Annotated[MealService, Depends(get_meal_service)]


@router.get("", response_model=list[Meal])
def list_meals(service: MealServiceDependency) -> list[Meal]:
    return service.list_meals()


@router.post("", response_model=Meal, status_code=status.HTTP_201_CREATED)
def create_meal(payload: MealCreate, service: MealServiceDependency) -> Meal:
    return service.create_meal(payload)


@router.get("/{meal_id}", response_model=Meal)
def get_meal(meal_id: str, service: MealServiceDependency) -> Meal:
    return service.get_meal(meal_id)


@router.patch("/{meal_id}", response_model=Meal)
def update_meal(meal_id: str, payload: MealUpdate, service: MealServiceDependency) -> Meal:
    return service.update_meal(meal_id, payload)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(meal_id: str, service: MealServiceDependency) -> Response:
    service.delete_meal(meal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

