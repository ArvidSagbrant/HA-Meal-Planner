from datetime import date, timedelta
from types import SimpleNamespace

from meal_planner.config import MqttSettings
from meal_planner.mqtt.publisher import MqttIntegration
from meal_planner.schemas import PlanDay, WeeklyPlan


class FakePlanService:
    def get_week(self, week_start: date) -> WeeklyPlan:
        return WeeklyPlan(
            week_start=week_start,
            week_end=week_start + timedelta(days=6),
            days=[
                PlanDay(date=week_start + timedelta(days=index), meal=None)
                for index in range(7)
            ],
        )


class FakeClient:
    def __init__(self) -> None:
        self.published: list[dict] = []
        self.subscriptions: list[tuple[str, int]] = []
        self.credentials: tuple[str, str | None] | None = None
        self.connected_to: tuple[str, int, int] | None = None
        self.tls_enabled = False
        self.loop_started = False
        self.disconnected = False

    def reconnect_delay_set(self, **_kwargs) -> None:
        pass

    def will_set(self, topic, payload, qos, retain) -> None:
        self.will = (topic, payload, qos, retain)

    def username_pw_set(self, username, password) -> None:
        self.credentials = (username, password)

    def tls_set(self) -> None:
        self.tls_enabled = True

    def connect_async(self, host, port, keepalive) -> None:
        self.connected_to = (host, port, keepalive)

    def loop_start(self) -> None:
        self.loop_started = True

    def subscribe(self, topic, qos) -> None:
        self.subscriptions.append((topic, qos))

    def publish(self, topic, payload, qos, retain):
        self.published.append(
            {"topic": topic, "payload": payload, "qos": qos, "retain": retain}
        )
        return SimpleNamespace(rc=0)

    def disconnect(self) -> None:
        self.disconnected = True

    def loop_stop(self) -> None:
        self.loop_started = False


def test_external_broker_connects_and_republishes_after_ha_birth() -> None:
    client = FakeClient()
    settings = MqttSettings(
        enabled=True,
        mode="external",
        host="mqtt.example",
        port=8883,
        username="meal-planner",
        password="secret",
        tls=True,
    )
    integration = MqttIntegration(
        settings,
        FakePlanService(),
        "en",
        client_factory=lambda: client,
        date_provider=lambda: date(2026, 8, 17),
    )

    integration.start()
    assert client.connected_to == ("mqtt.example", 8883, 60)
    assert client.credentials == ("meal-planner", "secret")
    assert client.tls_enabled is True
    assert client.will == ("meal_planner/status", "offline", 1, True)

    client.on_connect(client, None, None, 0, None)
    assert client.subscriptions == [("homeassistant/status", 1)]
    assert integration.status().connected is True
    assert {item["topic"] for item in client.published} >= {
        "homeassistant/sensor/meal_planner_today/config",
        "homeassistant/sensor/meal_planner_tomorrow/config",
        "meal_planner/today/state",
        "meal_planner/tomorrow/state",
        "meal_planner/status",
    }
    discovery = [item for item in client.published if item["topic"].endswith("/config")]
    assert all(item["retain"] for item in discovery)

    before = len(client.published)
    client.on_message(
        client,
        None,
        SimpleNamespace(topic="homeassistant/status", payload=b"online"),
    )
    assert len(client.published) > before

    integration.stop()
    assert client.published[-1]["payload"] == "offline"
    assert client.disconnected is True
    assert integration.status().connected is False


def test_disabled_mqtt_never_creates_a_client() -> None:
    created = False

    def factory():
        nonlocal created
        created = True
        return FakeClient()

    integration = MqttIntegration(
        MqttSettings(),
        FakePlanService(),
        "en",
        client_factory=factory,
    )
    integration.start()

    assert created is False
    assert integration.status().enabled is False
    assert integration.status().connected is False
