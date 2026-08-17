"""FastAPI dependency accessors."""

from fastapi import Request

from ..container import Container
from ..services.meals import MealService
from ..services.plans import PlanService


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_meal_service(request: Request) -> MealService:
    return get_container(request).meals


def get_plan_service(request: Request) -> PlanService:
    return get_container(request).plans

