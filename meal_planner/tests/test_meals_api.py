from pathlib import Path

from fastapi.testclient import TestClient

from meal_planner.config import Settings
from meal_planner.main import create_app


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


def test_nutrition_fields_are_validated_and_persisted(
    client: TestClient, meal_payload: dict
) -> None:
    response = client.post(
        "/api/meals",
        json={
            **meal_payload,
            "nutrition": {
                "calories_kcal": 620,
                "protein_g": 31.5,
                "carbohydrates_g": 72,
                "fat_g": 18,
                "fiber_g": 9,
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["nutrition"] == {
        "calories_kcal": 620.0,
        "protein_g": 31.5,
        "carbohydrates_g": 72.0,
        "fat_g": 18.0,
        "fiber_g": 9.0,
    }
    invalid = client.patch(
        f"/api/meals/{response.json()['id']}",
        json={"nutrition": {"fiber_g": -1}},
    )
    assert invalid.status_code == 422


def test_meal_images_are_stored_served_replaced_and_removed(
    client: TestClient, meal_payload: dict, data_dir: Path
) -> None:
    meal = client.post("/api/meals", json=meal_payload).json()
    png = b"\x89PNG\r\n\x1a\n" + b"first-image"

    uploaded = client.put(
        f"/api/meals/{meal['id']}/image",
        content=png,
        headers={"Content-Type": "image/png"},
    )

    assert uploaded.status_code == 200
    first = uploaded.json()
    assert first["image_mime_type"] == "image/png"
    assert first["image_size_bytes"] == len(png)
    first_path = data_dir / "images" / first["image_path"]
    assert first_path.read_bytes() == png
    served = client.get(f"/api/meals/{meal['id']}/image")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.content == png

    jpeg = b"\xff\xd8\xff" + b"replacement"
    replaced = client.put(f"/api/meals/{meal['id']}/image", content=jpeg)
    assert replaced.status_code == 200
    assert replaced.json()["image_mime_type"] == "image/jpeg"
    assert not first_path.exists()

    removed = client.delete(f"/api/meals/{meal['id']}/image")
    assert removed.status_code == 200
    assert removed.json()["image_path"] is None
    assert list((data_dir / "images").iterdir()) == []
    assert client.get(f"/api/meals/{meal['id']}/image").status_code == 404


def test_invalid_image_is_rejected_without_changing_meal(
    client: TestClient, meal_payload: dict
) -> None:
    meal = client.post("/api/meals", json=meal_payload).json()

    response = client.put(
        f"/api/meals/{meal['id']}/image",
        content=b"not an image",
    )

    assert response.status_code == 400
    assert response.json()["code"] == "ImageValidationError"
    assert client.get(f"/api/meals/{meal['id']}").json()["image_path"] is None


def test_deleting_meal_removes_its_local_image(
    client: TestClient, meal_payload: dict, data_dir: Path
) -> None:
    meal = client.post("/api/meals", json=meal_payload).json()
    uploaded = client.put(
        f"/api/meals/{meal['id']}/image",
        content=b"GIF89a" + b"image",
    ).json()
    image_path = data_dir / "images" / uploaded["image_path"]

    assert client.delete(f"/api/meals/{meal['id']}").status_code == 204
    assert not image_path.exists()


def test_startup_prunes_orphaned_image_files(data_dir: Path) -> None:
    image_directory = data_dir / "images"
    image_directory.mkdir(parents=True)
    orphan = image_directory / "orphan.png"
    orphan.write_bytes(b"\x89PNG\r\n\x1a\n")

    with TestClient(create_app(Settings(data_dir=data_dir))) as test_client:
        assert test_client.get("/api/health").status_code == 200

    assert not orphan.exists()
