from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from meal_planner.config import Settings
from meal_planner.main import create_app


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def client(data_dir: Path) -> Iterator[TestClient]:
    app = create_app(Settings(data_dir=data_dir, language="en", log_level="ERROR"))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def meal_payload() -> dict:
    return {
        "name": "Vegetable lasagne",
        "description": "A weekday-friendly lasagne",
        "preference": 4,
        "cooking_effort": 3,
        "meal_type": "dinner",
        "protein_source": "halloumi",
        "is_vegetarian": True,
        "tags": ["weekday", "family"],
        "nutrition": {"protein_g": 24},
    }
