from fastapi.testclient import TestClient


def test_meal_crud(client: TestClient, meal_payload: dict) -> None:
    create_response = client.post("/api/meals", json=meal_payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == meal_payload["name"]
    assert created["tags"] == ["weekday", "family"]
    assert created["protein_source"] == "halloumi"
    assert created["is_vegetarian"] is True

    list_response = client.get("/api/meals")
    assert list_response.status_code == 200
    assert [meal["id"] for meal in list_response.json()] == [created["id"]]

    update_response = client.patch(
        f"/api/meals/{created['id']}",
        json={
            "name": "Mushroom lasagne",
            "preference": 5,
            "is_vegetarian": False,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Mushroom lasagne"
    assert update_response.json()["description"] == meal_payload["description"]
    assert update_response.json()["is_vegetarian"] is False

    delete_response = client.delete(f"/api/meals/{created['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/meals/{created['id']}").status_code == 404


def test_mutations_notify_optional_integrations(
    client: TestClient, meal_payload: dict
) -> None:
    notifications: list[None] = []
    client.app.state.container.changes.subscribe(lambda: notifications.append(None))

    meal = client.post("/api/meals", json=meal_payload).json()
    client.patch(f"/api/meals/{meal['id']}", json={"preference": 5})
    client.put(
        "/api/plans/2026-08-17/days/2026-08-17",
        json={"meal_id": meal["id"]},
    )
    client.patch(
        "/api/plans/2026-08-17/days/2026-08-17/cooked",
        json={"is_cooked": True},
    )

    assert len(notifications) == 4


def test_duplicate_meal_name_is_rejected_case_insensitively(
    client: TestClient, meal_payload: dict
) -> None:
    assert client.post("/api/meals", json=meal_payload).status_code == 201
    duplicate = {**meal_payload, "name": meal_payload["name"].upper()}
    response = client.post("/api/meals", json=duplicate)
    assert response.status_code == 409
    assert response.json()["code"] == "ConflictError"


def test_meal_validation_is_enforced(client: TestClient, meal_payload: dict) -> None:
    response = client.post("/api/meals", json={**meal_payload, "preference": 8})
    assert response.status_code == 422


def test_protein_source_must_be_from_catalog(
    client: TestClient, meal_payload: dict
) -> None:
    response = client.post(
        "/api/meals",
        json={**meal_payload, "protein_source": "free text"},
    )

    assert response.status_code == 422


def test_required_fields_cannot_be_cleared(client: TestClient, meal_payload: dict) -> None:
    meal = client.post("/api/meals", json=meal_payload).json()

    response = client.patch(f"/api/meals/{meal['id']}", json={"tags": None})

    assert response.status_code == 422
