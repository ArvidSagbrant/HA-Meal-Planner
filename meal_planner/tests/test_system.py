from fastapi.testclient import TestClient

from meal_planner.config import Settings
from meal_planner.main import create_app


def test_health_and_settings(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/settings").json() == {
        "language": "en",
        "log_level": "ERROR",
        "protein_sources": [
            "poultry",
            "fish",
            "beef",
            "pork",
            "lamb",
            "seafood",
            "eggs",
            "halloumi",
            "tofu",
            "tempeh",
            "quorn",
            "legumes",
            "other",
        ],
        "planning": {
            "repeat_avoidance_weeks": 2,
            "vegetarian_target": 2,
            "preference_weight": 1.0,
            "recency_weight": 1.0,
            "effort_weight": 0.6,
            "variety_weight": 1.0,
            "weekday_effort_target": 2,
            "weekend_effort_target": 4,
        },
        "mqtt": {
            "enabled": False,
            "mode": "disabled",
            "broker": None,
            "tls": False,
            "discovery_prefix": "homeassistant",
            "topic_prefix": "meal_planner",
        },
        "ai": {
            "enabled": False,
            "provider": "disabled",
            "base_url": None,
            "model": None,
            "timeout_seconds": 30.0,
            "temperature": 0.2,
            "refinement_enabled": False,
            "suggestions_enabled": False,
        },
    }
    assert client.get("/api/mqtt/status").json() == {
        "enabled": False,
        "connected": False,
        "mode": "disabled",
        "broker": None,
        "last_error": None,
    }
    assert client.get("/api/ai/status").json() == {
        "enabled": False,
        "provider": "disabled",
        "model": None,
        "refinement_enabled": False,
        "suggestions_enabled": False,
        "last_action": None,
        "last_error": None,
    }


def test_frontend_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "data-i18n=\"app.title\"" in response.text
    assert '<select id="meal-protein"' in response.text
    assert 'id="meal-vegetarian"' in response.text
    assert 'id="mqtt-status"' in response.text
    assert 'id="suggest-meals"' in response.text


def test_protein_catalog_and_cooked_label_are_localized(
    client: TestClient,
) -> None:
    english = client.get("/locales/en.json").json()
    swedish = client.get("/locales/sv.json").json()

    assert english["proteinSources"]["poultry"] == "Poultry"
    assert swedish["proteinSources"]["poultry"] == "Fågel"
    assert english["week"]["cooked"] == "Cooked"
    assert swedish["week"]["cooked"] == "Tillagad"


def test_ingress_double_slash_reaches_api(
    client: TestClient, meal_payload: dict
) -> None:
    settings_response = client.get("http://testserver//api/settings")
    create_response = client.post(
        "http://testserver//api/meals",
        json=meal_payload,
    )

    assert settings_response.status_code == 200
    assert settings_response.json()["language"] == "en"
    assert create_response.status_code == 201
    assert create_response.json()["name"] == meal_payload["name"]


def test_ingress_only_mode_rejects_other_network_clients(tmp_path) -> None:
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            language="en",
            log_level="ERROR",
            ingress_only=True,
        )
    )
    with TestClient(app) as ingress_client:
        response = ingress_client.get("/api/health")

    assert response.status_code == 403
