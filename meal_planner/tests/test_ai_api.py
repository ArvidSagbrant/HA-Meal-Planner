import json
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient

from meal_planner.ai.models import MealSuggestions, PlanRefinementProposal
from meal_planner.ai.providers import AIProviderError
from meal_planner.config import AISettings, Settings
from meal_planner.main import create_app


WEEK_START = "2026-08-17"


class FakeAIProvider:
    def __init__(
        self,
        *,
        invalid_plan: bool = False,
        provider_failure: bool = False,
    ) -> None:
        self.invalid_plan = invalid_plan
        self.provider_failure = provider_failure
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return "fake"

    def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model,
    ):
        del system_prompt
        self.calls.append(response_model.__name__)
        if self.provider_failure:
            raise AIProviderError("AI provider could not be reached")
        if response_model is PlanRefinementProposal:
            payload = json.loads(user_prompt)
            current = payload["current_plan"]
            meal_ids = list(current.values())
            if self.invalid_plan:
                meal_ids[0] = "invented-meal-id"
            else:
                meal_ids.reverse()
            return PlanRefinementProposal.model_validate(
                {
                    "assignments": [
                        {"date": day, "meal_id": meal_id}
                        for day, meal_id in zip(current, meal_ids, strict=True)
                    ],
                    "summary": "Improved variety",
                }
            )
        if response_model is MealSuggestions:
            return MealSuggestions.model_validate(
                {
                    "suggestions": [
                        {
                            "name": "Bean tacos",
                            "description": "Quick tacos with black beans",
                            "cooking_effort": 2,
                            "meal_type": "dinner",
                            "protein_source": "legumes",
                            "is_vegetarian": True,
                            "tags": ["quick", "weekday"],
                        }
                    ]
                }
            )
        raise AssertionError("Unexpected response model")

    def close(self) -> None:
        pass


def ai_client(tmp_path: Path, provider: FakeAIProvider) -> TestClient:
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            language="en",
            log_level="ERROR",
            ai=AISettings(
                provider="llamacpp",
                base_url="http://llama.local/v1",
                model="local-model",
            ),
        )
    )
    app.state.container.ai.provider.close()
    app.state.container.ai.provider = provider
    return TestClient(app)


def create_meals(
    client: TestClient,
    meal_payload: dict,
    count: int = 8,
) -> list[dict]:
    meals = []
    proteins = ["poultry", "fish", "beef", "pork", "halloumi", "tofu", "lamb", "eggs"]
    for index in range(count):
        payload = deepcopy(meal_payload)
        payload.update(
            {
                "name": f"AI meal {index}",
                "protein_source": proteins[index],
                "is_vegetarian": proteins[index] in {"halloumi", "tofu"},
            }
        )
        meals.append(client.post("/api/meals", json=payload).json())
    return meals


def test_valid_ai_refinement_is_used(
    tmp_path: Path,
    meal_payload: dict,
) -> None:
    provider = FakeAIProvider()
    with ai_client(tmp_path, provider) as client:
        create_meals(client, meal_payload)
        response = client.post(f"/api/plans/{WEEK_START}/generate")
        status = client.get("/api/ai/status").json()

    assert response.status_code == 200
    assert provider.calls == ["PlanRefinementProposal"]
    assert status["last_action"] == "plan_refinement"
    assert status["last_error"] is None


def test_invalid_ai_plan_falls_back_to_deterministic_plan(
    tmp_path: Path,
    meal_payload: dict,
) -> None:
    provider = FakeAIProvider(invalid_plan=True)
    with ai_client(tmp_path, provider) as client:
        meals = create_meals(client, meal_payload)
        response = client.post(f"/api/plans/{WEEK_START}/generate")
        status = client.get("/api/ai/status").json()

    assert response.status_code == 200
    planned_ids = {day["meal"]["id"] for day in response.json()["days"]}
    assert planned_ids <= {meal["id"] for meal in meals}
    assert "unknown meal" in status["last_error"]


def test_provider_failure_falls_back_without_failing_generation(
    tmp_path: Path,
    meal_payload: dict,
) -> None:
    provider = FakeAIProvider(provider_failure=True)
    with ai_client(tmp_path, provider) as client:
        create_meals(client, meal_payload)
        response = client.post(f"/api/plans/{WEEK_START}/generate")
        status = client.get("/api/ai/status").json()

    assert response.status_code == 200
    assert all(day["meal"] for day in response.json()["days"])
    assert status["last_error"] == "AI provider could not be reached"


def test_ai_cannot_change_manual_assignments(
    tmp_path: Path,
    meal_payload: dict,
) -> None:
    provider = FakeAIProvider()
    with ai_client(tmp_path, provider) as client:
        meals = create_meals(client, meal_payload)
        manual_id = meals[-1]["id"]
        client.put(
            f"/api/plans/{WEEK_START}/days/2026-08-17",
            json={"meal_id": manual_id},
        )
        response = client.post(f"/api/plans/{WEEK_START}/generate")
        status = client.get("/api/ai/status").json()

    assert response.status_code == 200
    assert response.json()["days"][0]["meal"]["id"] == manual_id
    assert response.json()["days"][0]["is_manual_override"] is True
    assert "fixed assignment" in status["last_error"]


def test_meal_suggestions_are_previewed_but_not_persisted(tmp_path: Path) -> None:
    provider = FakeAIProvider()
    with ai_client(tmp_path, provider) as client:
        response = client.post(
            "/api/ai/suggestions",
            json={"count": 3, "preferences": "quick vegetarian"},
        )
        meals = client.get("/api/meals").json()

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Bean tacos"
    assert response.json()[0]["protein_source"] == "legumes"
    assert meals == []


def test_disabled_ai_suggestions_return_service_unavailable(client: TestClient) -> None:
    response = client.post(
        "/api/ai/suggestions",
        json={"count": 2, "preferences": ""},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "AIUnavailableError"
