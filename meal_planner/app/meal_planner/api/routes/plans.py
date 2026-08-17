"""Weekly plan and manual assignment endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from ...schemas import PlanAssignmentRequest, WeeklyPlan
from ...services.plans import PlanService
from ..dependencies import get_plan_service


router = APIRouter(prefix="/plans", tags=["plans"])
PlanServiceDependency = Annotated[PlanService, Depends(get_plan_service)]


@router.get("/{week_start}", response_model=WeeklyPlan)
def get_week(week_start: date, service: PlanServiceDependency) -> WeeklyPlan:
    return service.get_week(week_start)


@router.post("/{week_start}/generate", response_model=WeeklyPlan)
def generate_week(week_start: date, service: PlanServiceDependency) -> WeeklyPlan:
    return service.generate_week(week_start)


@router.put("/{week_start}/days/{meal_date}", response_model=WeeklyPlan)
def assign_meal(
    week_start: date,
    meal_date: date,
    payload: PlanAssignmentRequest,
    service: PlanServiceDependency,
) -> WeeklyPlan:
    return service.assign_meal(week_start, meal_date, payload.meal_id)


@router.delete("/{week_start}/days/{meal_date}", response_model=WeeklyPlan)
def clear_meal(
    week_start: date, meal_date: date, service: PlanServiceDependency
) -> WeeklyPlan:
    return service.clear_meal(week_start, meal_date)


@router.post("/{week_start}/days/{meal_date}/regenerate", response_model=WeeklyPlan)
def regenerate_day(
    week_start: date, meal_date: date, service: PlanServiceDependency
) -> WeeklyPlan:
    return service.regenerate_day(week_start, meal_date)
