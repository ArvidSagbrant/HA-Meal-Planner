from pathlib import Path

import pytest

from meal_planner.config import MqttSettings, Settings


def test_external_mqtt_settings_are_loaded_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    values = {
        "MEAL_PLANNER_DATA_DIR": str(tmp_path),
        "MEAL_PLANNER_MQTT_ENABLED": "true",
        "MEAL_PLANNER_MQTT_MODE": "external",
        "MEAL_PLANNER_MQTT_HOST": "broker.local",
        "MEAL_PLANNER_MQTT_PORT": "8883",
        "MEAL_PLANNER_MQTT_USERNAME": "user",
        "MEAL_PLANNER_MQTT_PASSWORD": "password",
        "MEAL_PLANNER_MQTT_TLS": "true",
        "MEAL_PLANNER_MQTT_TOPIC_PREFIX": "house/meals",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    settings = Settings.from_environment().mqtt

    assert settings.enabled is True
    assert settings.mode == "external"
    assert settings.host == "broker.local"
    assert settings.port == 8883
    assert settings.username == "user"
    assert settings.password == "password"
    assert settings.tls is True
    assert settings.topic_prefix == "house/meals"


@pytest.mark.parametrize("topic", ["", "/meal_planner", "meal_planner/", "meal/+", "meal/#"])
def test_invalid_mqtt_topic_prefix_is_rejected(topic: str) -> None:
    with pytest.raises(ValueError, match="Invalid MQTT topic"):
        MqttSettings(topic_prefix=topic)


def test_addon_requests_optional_supervisor_mqtt_service() -> None:
    addon_root = Path("/addon")
    if not addon_root.exists():
        addon_root = Path(__file__).parents[1]
    config = (addon_root / "config.yaml").read_text()
    run_script = (addon_root / "run.sh").read_text()

    assert "mqtt:want" in config
    assert "mqtt_host=\"$(bashio::services 'mqtt' 'host'" in run_script
    assert "MEAL_PLANNER_MQTT_MODE" in run_script
