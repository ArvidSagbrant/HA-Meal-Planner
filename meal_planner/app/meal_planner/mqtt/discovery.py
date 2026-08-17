"""Pure Home Assistant MQTT Discovery and state message builders."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .. import __version__
from ..config import MqttSettings
from ..schemas import PlanDay


DEVICE_IDENTIFIER = "meal_planner_addon"
ENTITY_KEYS = ("today", "tomorrow")
ENTITY_NAMES = {
    "en": {"today": "Today's meal", "tomorrow": "Tomorrow's meal"},
    "sv": {"today": "Dagens måltid", "tomorrow": "Morgondagens måltid"},
}
EMPTY_STATES = {"en": "No meal planned", "sv": "Ingen måltid planerad"}


@dataclass(frozen=True, slots=True)
class MqttMessage:
    topic: str
    payload: str
    qos: int = 1
    retain: bool = False


def availability_topic(settings: MqttSettings) -> str:
    return f"{settings.topic_prefix}/status"


def discovery_messages(
    settings: MqttSettings, language: str
) -> tuple[MqttMessage, ...]:
    names = ENTITY_NAMES.get(language, ENTITY_NAMES["en"])
    device = {
        "identifiers": [DEVICE_IDENTIFIER],
        "manufacturer": "HA Meal Planner",
        "model": "Home Assistant Add-on",
        "name": "Meal Planner",
        "sw_version": __version__,
    }
    origin = {
        "name": "HA Meal Planner",
        "sw_version": __version__,
        "support_url": "https://github.com/ArvidSagbrant/HA-Meal-Planner",
    }
    messages = []
    for key in ENTITY_KEYS:
        unique_id = f"meal_planner_{key}"
        payload = {
            "availability_topic": availability_topic(settings),
            "default_entity_id": f"sensor.{unique_id}",
            "device": device,
            "icon": "mdi:food",
            "json_attributes_topic": f"{settings.topic_prefix}/{key}/attributes",
            "name": names[key],
            "origin": origin,
            "state_topic": f"{settings.topic_prefix}/{key}/state",
            "unique_id": unique_id,
        }
        messages.append(
            MqttMessage(
                topic=(
                    f"{settings.discovery_prefix}/sensor/{unique_id}/config"
                ),
                payload=_json(payload),
                retain=True,
            )
        )
    return tuple(messages)


def state_messages(
    settings: MqttSettings,
    language: str,
    today: PlanDay,
    tomorrow: PlanDay,
) -> tuple[MqttMessage, ...]:
    messages = []
    for key, day in zip(ENTITY_KEYS, (today, tomorrow), strict=True):
        meal = day.meal
        state = meal.name if meal else EMPTY_STATES.get(language, EMPTY_STATES["en"])
        attributes: dict[str, object] = {
            "assignment_type": day.assignment_type,
            "date": day.date.isoformat(),
            "is_cooked": day.is_cooked,
            "is_manual_override": day.is_manual_override,
            "meal_id": meal.id if meal else None,
            "planned": meal is not None,
        }
        if meal:
            attributes.update(
                {
                    "cooking_effort": meal.cooking_effort,
                    "description": meal.description,
                    "is_vegetarian": meal.is_vegetarian,
                    "meal_type": meal.meal_type,
                    "preference": meal.preference,
                    "protein_source": meal.protein_source,
                    "tags": meal.tags,
                }
            )
        messages.extend(
            (
                MqttMessage(
                    topic=f"{settings.topic_prefix}/{key}/state",
                    payload=state,
                ),
                MqttMessage(
                    topic=f"{settings.topic_prefix}/{key}/attributes",
                    payload=_json(attributes),
                ),
            )
        )
    return tuple(messages)


def _json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
