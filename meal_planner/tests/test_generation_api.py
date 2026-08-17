from copy import deepcopy

from fastapi.testclient import TestClient


WEEK_START = "2026-08-17"


def create_meals(
    client: TestClient, meal_payload: dict, count: int = 16
) -> list[dict]:
    meals = []
    proteins = ["poultry", "fish", "halloumi", "beef"]
    for index in range(count):
        payload = deepcopy(meal_payload)
        payload.update(
            {
                "name": f"Meal {index:02d}",
                "preference": 1 + (index % 5),
                "cooking_effort": 1 + (index % 5),
                "protein_source": proteins[index % len(proteins)],
                "is_vegetarian": proteins[index % len(proteins)] == "halloumi",
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


def test_only_cooked_meals_are_used_for_repeat_avoidance(
    client: TestClient, meal_payload: dict
) -> None:
    create_meals(client, meal_payload, count=8)
    first = client.post(f"/api/plans/{WEEK_START}/generate").json()
    cooked_day = first["days"][0]
    cooked_id = cooked_day["meal"]["id"]
    response = client.patch(
        f"/api/plans/{WEEK_START}/days/{cooked_day['date']}/cooked",
        json={"is_cooked": True},
    )
    assert response.status_code == 200
    second = client.post("/api/plans/2026-08-24/generate").json()

    first_ids = set(assignments(first).values())
    second_ids = set(assignments(second).values())
    assert cooked_id not in second_ids
    assert len((first_ids - {cooked_id}) & second_ids) == 6


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


def test_cooked_day_is_locked_and_preserved_during_week_regeneration(
    client: TestClient, meal_payload: dict
) -> None:
    create_meals(client, meal_payload)
    original = client.post(f"/api/plans/{WEEK_START}/generate").json()
    target = original["days"][2]
    target_id = target["meal"]["id"]
    cooked_response = client.patch(
        f"/api/plans/{WEEK_START}/days/{target['date']}/cooked",
        json={"is_cooked": True},
    )
    assert cooked_response.status_code == 200
    assert cooked_response.json()["days"][2]["is_cooked"] is True

    regenerated = client.post(f"/api/plans/{WEEK_START}/generate").json()
    assert regenerated["days"][2]["meal"]["id"] == target_id
    assert regenerated["days"][2]["is_cooked"] is True

    change_response = client.delete(
        f"/api/plans/{WEEK_START}/days/{target['date']}"
    )
    regenerate_response = client.post(
        f"/api/plans/{WEEK_START}/days/{target['date']}/regenerate"
    )
    assert change_response.status_code == 409
    assert change_response.json()["code"] == "CookedDayError"
    assert regenerate_response.status_code == 409
    assert regenerate_response.json()["code"] == "CookedDayError"


def test_cooked_mark_can_be_removed_before_editing(
    client: TestClient, meal_payload: dict
) -> None:
    meal = create_meals(client, meal_payload, count=1)[0]
    target = "2026-08-17"
    client.put(
        f"/api/plans/{WEEK_START}/days/{target}",
        json={"meal_id": meal["id"]},
    )
    client.patch(
        f"/api/plans/{WEEK_START}/days/{target}/cooked",
        json={"is_cooked": True},
    )

    unmark = client.patch(
        f"/api/plans/{WEEK_START}/days/{target}/cooked",
        json={"is_cooked": False},
    )
    clear = client.delete(f"/api/plans/{WEEK_START}/days/{target}")

    assert unmark.status_code == 200
    assert unmark.json()["days"][0]["is_cooked"] is False
    assert clear.status_code == 200
    assert clear.json()["days"][0]["meal"] is None


def test_empty_day_cannot_be_marked_cooked(client: TestClient) -> None:
    response = client.patch(
        f"/api/plans/{WEEK_START}/days/2026-08-17/cooked",
        json={"is_cooked": True},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "CookedDayError"
