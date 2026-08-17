"""Health and non-secret runtime configuration endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ...container import Container
from ...schemas import RuntimeSettings
from ..dependencies import get_container


router = APIRouter(tags=["system"])
ContainerDependency = Annotated[Container, Depends(get_container)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/settings", response_model=RuntimeSettings)
def runtime_settings(container: ContainerDependency) -> RuntimeSettings:
    return RuntimeSettings(
        language=container.settings.language,
        log_level=container.settings.log_level,
    )

