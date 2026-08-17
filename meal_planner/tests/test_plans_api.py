from pathlib import Path

from fastapi.testclient import TestClient

from meal_planner.config import Settings
from meal_planner.main import create_app


WEEK_START = "2026-08-17"


def test_week_contains_seven_days(client: TestClient) -> None:
    response = client.get(f"/api/plans/{WEEK_START}")
    assert response.status_code == 200
    plan = response.json()
    assert plan["week_start"] == WEEK_START
    assert plan["week_end"] == "2026-08-23"
    assert [day["date"] for day in plan["days"]] == [
        "2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20",
        "2026-08-21", "2026-08-22", "2026-08-23",
    ]


def test_manual_assignment_and_clear(client: TestClient, meal_payload: dict) -> None:
    meal = client.post("/api/meals", json=meal_payload).json()
    assigned_response = client.put(
        f"/api/plans/{WEEK_START}/days/2026-08-19",
        json={"meal_id": meal["id"]},
    )
    assert assigned_response.status_code == 200
    assigned_day = assigned_response.json()["days"][2]
    assert assigned_day["meal"]["id"] == meal["id"]
    assert assigned_day["assignment_type"] == "manual"
    assert assigned_day["is_manual_override"] is True

    clear_response = client.delete(f"/api/plans/{WEEK_START}/days/2026-08-19")
    assert clear_response.status_code == 200
    cleared_day = clear_response.json()["days"][2]
    assert cleared_day["meal"] is None
    assert cleared_day["is_manual_override"] is False


def test_assignment_survives_application_restart(
    client: TestClient, data_dir: Path, meal_payload: dict
) -> None:
    meal = client.post("/api/meals", json=meal_payload).json()
    client.put(
        f"/api/plans/{WEEK_START}/days/2026-08-21",
        json={"meal_id": meal["id"]},
    )
    restarted_app = create_app(Settings(data_dir=data_dir, language="en", log_level="ERROR"))
    with TestClient(restarted_app) as restarted_client:
        plan = restarted_client.get(f"/api/plans/{WEEK_START}").json()
    assert plan["days"][4]["meal"]["name"] == meal_payload["name"]


def test_deleting_meal_clears_existing_assignment(
    client: TestClient, meal_payload: dict
) -> None:
    meal = client.post("/api/meals", json=meal_payload).json()
    client.put(
        f"/api/plans/{WEEK_START}/days/2026-08-17",
        json={"meal_id": meal["id"]},
    )
    assert client.delete(f"/api/meals/{meal['id']}").status_code == 204
    plan = client.get(f"/api/plans/{WEEK_START}").json()
    assert plan["days"][0]["meal"] is None
    assert plan["days"][0]["is_manual_override"] is False


def test_week_start_must_be_monday(client: TestClient) -> None:
    response = client.get("/api/plans/2026-08-18")
    assert response.status_code == 400
    assert response.json()["code"] == "InvalidOperationError"


def test_meal_date_must_belong_to_week(client: TestClient, meal_payload: dict) -> None:
    meal = client.post("/api/meals", json=meal_payload).json()
    response = client.put(
        f"/api/plans/{WEEK_START}/days/2026-08-24",
        json={"meal_id": meal["id"]},
    )
    assert response.status_code == 400
