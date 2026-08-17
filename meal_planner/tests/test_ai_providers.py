import json

import httpx
import pytest

from meal_planner.ai.models import MealSuggestions
from meal_planner.ai.providers import (
    AIProviderError,
    LlamaCppProvider,
    OpenAIResponsesProvider,
)
from meal_planner.config import AISettings


VALID_SUGGESTIONS = {
    "suggestions": [
        {
            "name": "Lentil stew",
            "description": "A warming weekday stew",
            "cooking_effort": 2,
            "meal_type": "dinner",
            "protein_source": "legumes",
            "is_vegetarian": True,
            "tags": ["weekday"],
        }
    ]
}


def test_openai_provider_uses_responses_structured_output() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        assert request.url == "https://api.openai.com/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(VALID_SUGGESTIONS),
                            }
                        ],
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAIResponsesProvider(
        AISettings(
            provider="openai",
            base_url="https://api.openai.com/v1/",
            api_key="test-key",
            model="test-model",
        ),
        client,
    )

    result = provider.complete_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=MealSuggestions,
    )

    assert result.suggestions[0].name == "Lentil stew"
    assert captured["text"]["format"]["type"] == "json_schema"
    assert captured["text"]["format"]["strict"] is True
    assert captured["text"]["format"]["schema"]["additionalProperties"] is False


def test_llamacpp_provider_uses_openai_compatible_chat_completions() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        assert request.url == "http://llama.local:8080/v1/chat/completions"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(VALID_SUGGESTIONS)}}
                ]
            },
        )

    provider = LlamaCppProvider(
        AISettings(
            provider="llamacpp",
            base_url="http://llama.local:8080/v1",
            model="local-model",
        ),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = provider.complete_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=MealSuggestions,
    )

    assert result.suggestions[0].protein_source == "legumes"
    assert captured["response_format"]["type"] == "json_schema"
    assert captured["response_format"]["json_schema"]["strict"] is True


def test_provider_rejects_invalid_structured_data() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": '{"suggestions":[{"name":"x"}]}'}}
                    ]
                },
            )
        )
    )
    provider = LlamaCppProvider(
        AISettings(
            provider="llamacpp",
            base_url="http://llama.local/v1",
            model="local-model",
        ),
        client,
    )

    with pytest.raises(AIProviderError, match="failed validation"):
        provider.complete_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=MealSuggestions,
        )


def test_openai_provider_requires_api_key_without_network_request() -> None:
    provider = OpenAIResponsesProvider(
        AISettings(
            provider="openai",
            base_url="https://api.openai.com/v1",
            model="test-model",
        ),
        httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: pytest.fail("request must not be sent")
            )
        ),
    )

    with pytest.raises(AIProviderError, match="API key"):
        provider.complete_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=MealSuggestions,
        )
