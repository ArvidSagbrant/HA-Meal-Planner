from fastapi.testclient import TestClient

from meal_planner.config import Settings
from meal_planner.main import create_app


def test_health_and_settings(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/settings").json() == {
        "language": "en",
        "log_level": "ERROR",
    }


def test_frontend_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "data-i18n=\"app.title\"" in response.text


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
