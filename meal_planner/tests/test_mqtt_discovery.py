import json
from datetime import date, datetime, timezone

from meal_planner.config import MqttSettings
from meal_planner.mqtt.discovery import discovery_messages, state_messages
from meal_planner.schemas import Meal, PlanDay


SETTINGS = MqttSettings(
    enabled=True,
    mode="external",
    host="broker.example",
    topic_prefix="family/meals",
)


def test_discovery_uses_stable_entity_and_device_ids() -> None:
    messages = discovery_messages(SETTINGS, "sv")

    assert [message.topic for message in messages] == [
        "homeassistant/sensor/meal_planner_today/config",
        "homeassistant/sensor/meal_planner_tomorrow/config",
    ]
    assert all(message.retain and message.qos == 1 for message in messages)
    today = json.loads(messages[0].payload)
    tomorrow = json.loads(messages[1].payload)
    assert today["unique_id"] == "meal_planner_today"
    assert today["default_entity_id"] == "sensor.meal_planner_today"
    assert today["name"] == "Dagens måltid"
    assert tomorrow["unique_id"] == "meal_planner_tomorrow"
    assert tomorrow["default_entity_id"] == "sensor.meal_planner_tomorrow"
    assert today["device"]["identifiers"] == ["meal_planner_addon"]
    assert tomorrow["device"]["identifiers"] == ["meal_planner_addon"]


def test_state_contains_meal_details_and_localized_empty_state() -> None:
    meal = Meal(
        id="meal-1",
        name="Halloumigryta",
        description="Med tomat",
        preference=5,
        cooking_effort=2,
        meal_type="dinner",
        protein_source="halloumi",
        is_vegetarian=True,
        tags=["snabb"],
        created_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
        updated_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
    )
    messages = state_messages(
        SETTINGS,
        "sv",
        PlanDay(
            date=date(2026, 8, 17),
            meal=meal,
            assignment_type="manual",
            is_manual_override=True,
            is_cooked=True,
        ),
        PlanDay(date=date(2026, 8, 18), meal=None),
    )

    assert messages[0].topic == "family/meals/today/state"
    assert messages[0].payload == "Halloumigryta"
    attributes = json.loads(messages[1].payload)
    assert attributes["meal_id"] == "meal-1"
    assert attributes["is_cooked"] is True
    assert attributes["is_vegetarian"] is True
    assert attributes["protein_source"] == "halloumi"
    assert messages[2].payload == "Ingen måltid planerad"
    assert json.loads(messages[3].payload)["planned"] is False
