"""Provider abstraction for strict structured AI responses."""

from __future__ import annotations

from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..config import AISettings


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class AIProviderError(Exception):
    """Raised when a provider cannot return a validated structured response."""


class AIProvider(Protocol):
    @property
    def name(self) -> str: ...

    def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel: ...

    def close(self) -> None: ...


class DisabledAIProvider:
    name = "disabled"

    def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        del system_prompt, user_prompt, response_model
        raise AIProviderError("No AI provider is configured")

    def close(self) -> None:
        pass


class HTTPAIProvider:
    name = "http"

    def __init__(
        self,
        settings: AISettings,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=settings.timeout_seconds)

    def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        schema = response_model.model_json_schema()
        try:
            response = self.client.post(
                self._endpoint(),
                headers=self._headers(),
                json=self._payload(system_prompt, user_prompt, response_model, schema),
            )
            response.raise_for_status()
            content = self._extract_content(response.json())
            return response_model.model_validate_json(content)
        except ValidationError as error:
            raise AIProviderError("AI returned data that failed validation") from error
        except (ValueError, KeyError, TypeError) as error:
            raise AIProviderError("AI returned an invalid response envelope") from error
        except httpx.TimeoutException as error:
            raise AIProviderError("AI request timed out") from error
        except httpx.HTTPStatusError as error:
            raise AIProviderError(
                f"AI provider returned HTTP {error.response.status_code}"
            ) from error
        except httpx.HTTPError as error:
            raise AIProviderError("AI provider could not be reached") from error

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def _endpoint(self) -> str:
        raise NotImplementedError

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        return headers

    def _payload(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        schema: dict,
    ) -> dict:
        raise NotImplementedError

    def _extract_content(self, payload: dict) -> str:
        raise NotImplementedError


class OpenAIResponsesProvider(HTTPAIProvider):
    name = "openai"

    def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        if not self.settings.api_key:
            raise AIProviderError("OpenAI API key is not configured")
        return super().complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
        )

    def _endpoint(self) -> str:
        return f"{self.settings.base_url.rstrip('/')}/responses"

    def _payload(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        schema: dict,
    ) -> dict:
        return {
            "model": self.settings.model,
            "input": [
                {"role": "developer", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": response_model.__name__.lower(),
                    "strict": True,
                    "schema": schema,
                }
            },
        }

    def _extract_content(self, payload: dict) -> str:
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]
        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "refusal":
                    raise AIProviderError("OpenAI refused the structured request")
                if content.get("type") == "output_text" and isinstance(
                    content.get("text"), str
                ):
                    return content["text"]
        raise AIProviderError("OpenAI response did not contain output text")


class LlamaCppProvider(HTTPAIProvider):
    name = "llamacpp"

    def _endpoint(self) -> str:
        return f"{self.settings.base_url.rstrip('/')}/chat/completions"

    def _payload(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        schema: dict,
    ) -> dict:
        return {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__.lower(),
                    "strict": True,
                    "schema": schema,
                },
            },
        }

    def _extract_content(self, payload: dict) -> str:
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("completion content must be text")
        return content


def build_ai_provider(
    settings: AISettings,
    *,
    client: httpx.Client | None = None,
) -> AIProvider:
    if settings.provider == "openai":
        return OpenAIResponsesProvider(settings, client)
    if settings.provider == "llamacpp":
        return LlamaCppProvider(settings, client)
    return DisabledAIProvider()
