from pathlib import Path

import pytest

from meal_planner.config import AISettings, Settings


def test_openai_configuration_uses_safe_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MEAL_PLANNER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MEAL_PLANNER_AI_PROVIDER", "openai")
    monkeypatch.setenv("MEAL_PLANNER_AI_API_KEY", "super-secret")

    settings = Settings.from_environment().ai

    assert settings.enabled is True
    assert settings.base_url == "https://api.openai.com/v1"
    assert settings.model == "gpt-5-mini"
    assert settings.timeout_seconds == 30
    assert settings.refinement_enabled is True
    assert "super-secret" not in repr(settings)


def test_llamacpp_configuration_does_not_require_an_api_key() -> None:
    settings = AISettings(
        provider="llamacpp",
        base_url="http://llama.local:8080/v1",
        model="local-model",
    )

    assert settings.enabled is True
    assert settings.api_key == ""


@pytest.mark.parametrize("base_url", ["localhost:8080/v1", "ftp://server/v1", " https://api.example/v1"])
def test_ai_base_url_must_be_http_or_https(base_url: str) -> None:
    with pytest.raises(ValueError, match="HTTP"):
        AISettings(
            provider="llamacpp",
            base_url=base_url,
            model="local-model",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [("timeout_seconds", 0), ("timeout_seconds", 301), ("temperature", -0.1), ("temperature", 2.1)],
)
def test_invalid_advanced_ai_parameters_are_rejected(field: str, value: float) -> None:
    values = {
        "provider": "llamacpp",
        "base_url": "http://llama.local/v1",
        "model": "local-model",
        field: value,
    }

    with pytest.raises(ValueError):
        AISettings(**values)


def test_addon_configuration_marks_ai_key_as_password() -> None:
    addon_root = Path("/addon")
    if not addon_root.exists():
        addon_root = Path(__file__).parents[1]
    config = (addon_root / "config.yaml").read_text()
    run_script = (addon_root / "run.sh").read_text()

    assert "ai_provider: list(disabled|openai|llamacpp)" in config
    assert "ai_api_key: password" in config
    assert "MEAL_PLANNER_AI_API_KEY" in run_script
