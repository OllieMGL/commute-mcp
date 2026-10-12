import runpy

import httpx
import pytest
from mcp.server.mcpserver import MCPServer

from commute_mcp.server import get_departures, get_weather, plan_journey, resolve_station
from commute_mcp.weather import FORECAST_URL

RAIL_API = "https://api1.raildata.org.uk/"


# resolve_station


def test_resolve_exact_name_has_no_note():
    station, note = resolve_station("Reading")
    assert station["stationName"] == "Reading"
    assert note is None


def test_resolve_ambiguous_name_lists_other_matches():
    station, note = resolve_station("Bristol")
    assert station["stationName"] == "Bristol Parkway"
    assert "Bristol Temple Meads" in note


def test_resolve_typo_says_it_used_the_closest_match():
    station, note = resolve_station("Narnia")
    assert station["stationName"] == "Nairn"
    assert note.startswith("No station called 'Narnia'")


def test_resolve_nothing_found():
    assert resolve_station("qqqqqqqqqq") == (None, None)


# get_departures


async def test_get_departures(respx_mock, departure_board_data):
    respx_mock.get(url__startswith=RAIL_API).mock(
        return_value=httpx.Response(200, json=departure_board_data)
    )
    result = await get_departures("Guildford", "London Waterloo")

    assert result["station"] == "Guildford"
    assert result["destination"] == "London Waterloo"
    assert result["notes"] == []
    assert result["departures"][0]["arrival_expected"] == "18:43"


async def test_get_departures_notes_a_guessed_station(respx_mock, departure_board_data):
    respx_mock.get(url__startswith=RAIL_API).mock(
        return_value=httpx.Response(200, json=departure_board_data)
    )
    result = await get_departures("Bristol")

    assert len(result["notes"]) == 1
    assert "Bristol Temple Meads" in result["notes"][0]


async def test_get_departures_unknown_station(respx_mock):
    # respx_mock with no routes: any request at all would fail this test
    result = await get_departures("qqqqqqqqqq")
    assert result == {"error": "No station found matching 'qqqqqqqqqq'."}


async def test_get_departures_unknown_destination(respx_mock):
    result = await get_departures("Guildford", "qqqqqqqqqq")
    assert result == {"error": "No station found matching 'qqqqqqqqqq'."}


async def test_get_departures_missing_api_key(monkeypatch, respx_mock):
    monkeypatch.delenv("RAIL_API_KEY")
    result = await get_departures("Guildford")
    assert "RAIL_API_KEY is not set" in result["error"]


async def test_get_departures_api_down(respx_mock):
    respx_mock.get(url__startswith=RAIL_API).mock(return_value=httpx.Response(503))
    result = await get_departures("Guildford")
    assert result["error"].startswith("Could not get departures from National Rail")


# get_weather


async def test_get_weather(respx_mock, current_weather_data):
    respx_mock.get(url__startswith=FORECAST_URL).mock(
        return_value=httpx.Response(200, json=current_weather_data)
    )
    result = await get_weather("Guildford")

    assert result["station"] == "Guildford"
    assert result["weather"].conditions == "Rain"
    assert result["notes"] == []


async def test_get_weather_api_down(respx_mock):
    respx_mock.get(url__startswith=FORECAST_URL).mock(return_value=httpx.Response(500))
    result = await get_weather("Guildford")
    assert result["error"].startswith("Could not get the weather")


async def test_get_weather_unknown_station(respx_mock):
    result = await get_weather("qqqqqqqqqq")
    assert result == {"error": "No station found matching 'qqqqqqqqqq'."}


# plan_journey


async def test_plan_journey_forecast_ends_at_latest_arrival(
    respx_mock, departure_board_data, hourly_forecast_data
):
    respx_mock.get(url__startswith=RAIL_API).mock(
        return_value=httpx.Response(200, json=departure_board_data)
    )
    respx_mock.get(url__startswith=FORECAST_URL).mock(
        return_value=httpx.Response(200, json=hourly_forecast_data)
    )
    result = await plan_journey("Guildford", "London Waterloo")

    # The forecast starts at 18:00. Arrivals are 18:43 and 19:05 ("On time",
    # so the scheduled time is used), so it needs 18:00 and 19:00, not 20:00
    forecast_hours = [hour["time"].hour for hour in result["destination_forecast"]]
    assert forecast_hours == [18, 19]


async def test_plan_journey_still_returns_trains_if_weather_fails(
    respx_mock, departure_board_data
):
    respx_mock.get(url__startswith=RAIL_API).mock(
        return_value=httpx.Response(200, json=departure_board_data)
    )
    respx_mock.get(url__startswith=FORECAST_URL).mock(return_value=httpx.Response(500))
    result = await plan_journey("Guildford", "London Waterloo")

    assert len(result["departures"]) == 2
    assert result["destination_forecast"] is None
    assert result["forecast_error"] == "Could not get the weather forecast."


async def test_plan_journey_passes_errors_through(respx_mock):
    result = await plan_journey("qqqqqqqqqq", "London Waterloo")
    assert result == {"error": "No station found matching 'qqqqqqqqqq'."}


# Entry point


# Other tests have already imported server.py, so runpy warns that it's
# running it a second time. That's expected here.
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_running_the_module_starts_the_server(monkeypatch):
    # .mcp.json starts the server with `python -m commute_mcp.server`.
    # This runs the file the same way and checks mcp.run() gets called.
    calls = []
    monkeypatch.setattr(MCPServer, "run", lambda self, *args, **kwargs: calls.append(self))

    runpy.run_module("commute_mcp.server", run_name="__main__")

    assert len(calls) == 1
