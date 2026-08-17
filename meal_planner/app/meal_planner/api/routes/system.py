"""Health and non-secret runtime configuration endpoints."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from ...catalog import PROTEIN_SOURCES
from ...container import Container
from ...schemas import MqttStatusView, RuntimeSettings
from ..dependencies import get_container


router = APIRouter(tags=["system"])
ContainerDependency = Annotated[Container, Depends(get_container)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/settings", response_model=RuntimeSettings)
def runtime_settings(container: ContainerDependency) -> RuntimeSettings:
    mqtt = container.mqtt.status()
    return RuntimeSettings(
        language=container.settings.language,
        log_level=container.settings.log_level,
        protein_sources=list(PROTEIN_SOURCES),
        planning=asdict(container.settings.planner),
        mqtt={
            "enabled": mqtt.enabled,
            "mode": mqtt.mode,
            "broker": mqtt.broker,
            "tls": container.settings.mqtt.tls,
            "discovery_prefix": container.settings.mqtt.discovery_prefix,
            "topic_prefix": container.settings.mqtt.topic_prefix,
        },
        ai={
            "enabled": container.settings.ai.enabled,
            "provider": container.settings.ai.provider,
            "base_url": (
                container.settings.ai.base_url
                if container.settings.ai.enabled
                else None
            ),
            "model": (
                container.settings.ai.model if container.settings.ai.enabled else None
            ),
            "timeout_seconds": container.settings.ai.timeout_seconds,
            "temperature": container.settings.ai.temperature,
            "refinement_enabled": (
                container.settings.ai.enabled
                and container.settings.ai.refinement_enabled
            ),
            "suggestions_enabled": (
                container.settings.ai.enabled
                and container.settings.ai.suggestions_enabled
            ),
        },
    )


@router.get("/mqtt/status", response_model=MqttStatusView)
def mqtt_status(container: ContainerDependency) -> MqttStatusView:
    return MqttStatusView.model_validate(asdict(container.mqtt.status()))
