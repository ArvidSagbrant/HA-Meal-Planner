"""Optional AI status and meal suggestion endpoints."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from ...ai import AIProviderError
from ...container import Container
from ...errors import AIUnavailableError
from ...schemas import AIStatusView, MealSuggestionRequest
from ...ai.models import MealSuggestion
from ..dependencies import get_container


router = APIRouter(prefix="/ai", tags=["ai"])
ContainerDependency = Annotated[Container, Depends(get_container)]


@router.get("/status", response_model=AIStatusView)
def ai_status(container: ContainerDependency) -> AIStatusView:
    return AIStatusView.model_validate(asdict(container.ai.status()))


@router.post("/suggestions", response_model=list[MealSuggestion])
def suggest_meals(
    payload: MealSuggestionRequest,
    container: ContainerDependency,
) -> list[MealSuggestion]:
    try:
        return container.ai.suggest_meals(
            count=payload.count,
            preferences=payload.preferences.strip(),
        )
    except AIProviderError as error:
        raise AIUnavailableError(str(error)) from error
