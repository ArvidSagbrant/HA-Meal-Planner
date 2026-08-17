from copy import deepcopy

from fastapi.testclient import TestClient


WEEK_START = "2026-08-17"


def create_meals(
    client: TestClient, meal_payload: dict, count: int = 16
) -> list[dict]:
    meals = []
    proteins = ["chicken", "fish", "vegetarian", "beef"]
    for index in range(count):
        payload = deepcopy(meal_payload)
        payload.update(
            {
                "name": f"Meal {index:02d}",
                "preference": 1 + (index % 5),
                "cooking_effort": 1 + (index % 5),
                "protein_source": proteins[index % len(proteins)],
                "tags": [f"tag-{index % 3}"],
            }
        )
        response = client.post("/api/meals", json=payload)
        assert response.status_code == 201
        meals.append(response.json())
    return meals


def assignments(plan: dict) -> dict[str, str | None]:
    return {
        day["date"]: day["meal"]["id"] if day["meal"] else None
        for day in plan["days"]
    }


def test_generate_full_week_and_preserve_manual_override(
    client: TestClient, meal_payload: dict
) -> None:
    meals = create_meals(client, meal_payload)
    manual_id = meals[-1]["id"]
    manual_date = "2026-08-19"
    client.put(
        f"/api/plans/{WEEK_START}/days/{manual_date}",
        json={"meal_id": manual_id},
    )

    response = client.post(f"/api/plans/{WEEK_START}/generate")

    assert response.status_code == 200
    plan = response.json()
    selected = [day["meal"]["id"] for day in plan["days"]]
    assert len(set(selected)) == 7
    manual_day = next(day for day in plan["days"] if day["date"] == manual_date)
    assert manual_day["meal"]["id"] == manual_id
    assert manual_day["assignment_type"] == "manual"
    assert manual_day["is_manual_override"] is True
    assert all(
        day["assignment_type"] == "generated"
        for day in plan["days"]
        if day["date"] != manual_date
    )


def test_previous_week_is_used_for_repeat_avoidance(
    client: TestClient, meal_payload: dict
) -> None:
    create_meals(client, meal_payload)
    first = client.post(f"/api/plans/{WEEK_START}/generate").json()
    second = client.post("/api/plans/2026-08-24/generate").json()

    assert set(assignments(first).values()).isdisjoint(assignments(second).values())


def test_regenerate_one_day_changes_only_that_day(
    client: TestClient, meal_payload: dict
) -> None:
    create_meals(client, meal_payload)
    original = client.post(f"/api/plans/{WEEK_START}/generate").json()
    target = "2026-08-20"

    response = client.post(
        f"/api/plans/{WEEK_START}/days/{target}/regenerate"
    )

    assert response.status_code == 200
    regenerated = response.json()
    before = assignments(original)
    after = assignments(regenerated)
    assert after[target] != before[target]
    assert {day: meal_id for day, meal_id in after.items() if day != target} == {
        day: meal_id for day, meal_id in before.items() if day != target
    }


def test_failed_generation_leaves_existing_plan_unchanged(
    client: TestClient, meal_payload: dict
) -> None:
    meal = create_meals(client, meal_payload, count=1)[0]
    client.put(
        f"/api/plans/{WEEK_START}/days/2026-08-17",
        json={"meal_id": meal["id"]},
    )
    before = client.get(f"/api/plans/{WEEK_START}").json()

    response = client.post(f"/api/plans/{WEEK_START}/generate")

    assert response.status_code == 409
    assert response.json()["code"] == "PlanningError"
    assert client.get(f"/api/plans/{WEEK_START}").json() == before


def test_manual_duplicates_are_rejected(
    client: TestClient, meal_payload: dict
) -> None:
    meal = create_meals(client, meal_payload, count=1)[0]
    client.put(
        f"/api/plans/{WEEK_START}/days/2026-08-17",
        json={"meal_id": meal["id"]},
    )

    response = client.put(
        f"/api/plans/{WEEK_START}/days/2026-08-18",
        json={"meal_id": meal["id"]},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "DuplicateAssignmentError"


def test_manual_day_cannot_be_regenerated(
    client: TestClient, meal_payload: dict
) -> None:
    meal = create_meals(client, meal_payload, count=1)[0]
    client.put(
        f"/api/plans/{WEEK_START}/days/2026-08-17",
        json={"meal_id": meal["id"]},
    )

    response = client.post(
        f"/api/plans/{WEEK_START}/days/2026-08-17/regenerate"
    )

    assert response.status_code == 409
    assert response.json()["code"] == "PlanningError"
