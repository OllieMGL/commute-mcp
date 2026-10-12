# Shared setup for every test. pytest loads this file automatically

import json
from pathlib import Path

import pytest

from commute_mcp.rail import DEPARTURES_CACHE
from commute_mcp.weather import WEATHER_CACHE

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    # Read the file fresh each time, so a test that changes the dict
    # can't affect another test
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def clear_caches():
    # The caches live at module level, so without this a board cached by one
    # test would be returned to the next test instead of the mocked response
    DEPARTURES_CACHE.entries.clear()
    WEATHER_CACHE.entries.clear()


@pytest.fixture(autouse=True)
def fake_api_key(monkeypatch):
    # Never use the real key from .env in tests
    monkeypatch.setenv("RAIL_API_KEY", "test-key")


@pytest.fixture
def departure_board_data():
    return load_fixture("departure_board.json")


@pytest.fixture
def bus_board_data():
    return load_fixture("departure_board_buses.json")


@pytest.fixture
def hourly_forecast_data():
    return load_fixture("hourly_forecast.json")


@pytest.fixture
def current_weather_data():
    return load_fixture("current_weather.json")
