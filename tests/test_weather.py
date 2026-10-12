from datetime import datetime

import httpx
import pytest

from commute_mcp.weather import (
    FORECAST_URL,
    describe_weather_code,
    get_current_weather,
    get_hourly_forecast,
    hours_until,
    parse_current_weather,
    parse_hourly_forecast,
)


# hours_until


def test_hours_until_same_hour():
    assert hours_until(18, "18:45") == 1


def test_hours_until_later_hour():
    assert hours_until(18, "19:16") == 2


def test_hours_until_past_midnight():
    # 23:00 to 00:20 wraps round, so it's 2 hours, not a negative number
    assert hours_until(23, "00:20") == 2


def test_hours_until_several_hours_past_midnight():
    assert hours_until(20, "00:42") == 5


# describe_weather_code


def test_known_weather_code():
    assert describe_weather_code(61) == "Rain"


def test_unknown_weather_code():
    assert describe_weather_code(4) == "Unknown"


# Parsers


def test_parse_current_weather(current_weather_data):
    weather = parse_current_weather(current_weather_data)
    assert weather.time == datetime(2026, 10, 12, 18, 15)
    assert weather.conditions == "Rain"
    assert weather.temperature_c == 14.2
    assert weather.feels_like_c == 12.9
    assert weather.precipitation_mm == 0.4
    assert weather.wind_speed_kmh == 15.1


def test_parse_current_weather_missing_section():
    with pytest.raises(ValueError):
        parse_current_weather({})


def test_parse_hourly_forecast(hourly_forecast_data):
    forecast = parse_hourly_forecast(hourly_forecast_data)
    assert len(forecast) == 3
    assert forecast[0].time == datetime(2026, 10, 12, 18, 0)
    assert forecast[1].conditions == "Rain"
    assert forecast[1].precipitation_probability == 60


def test_parse_hourly_forecast_missing_section():
    with pytest.raises(ValueError):
        parse_hourly_forecast({})


def test_parse_hourly_forecast_lists_of_different_lengths(hourly_forecast_data):
    # zip(strict=True) refuses to silently drop hours that don't line up
    hourly_forecast_data["hourly"]["temperature_2m"].pop()
    with pytest.raises(ValueError):
        parse_hourly_forecast(hourly_forecast_data)


# API calls (respx fakes Open-Meteo, so no real request is made)


async def test_get_hourly_forecast_sends_params(respx_mock, hourly_forecast_data):
    route = respx_mock.get(url__startswith=FORECAST_URL).mock(
        return_value=httpx.Response(200, json=hourly_forecast_data)
    )
    await get_hourly_forecast(51.5, -0.12, hours=3)

    params = route.calls.last.request.url.params
    assert params["forecast_hours"] == "3"
    assert params["timezone"] == "Europe/London"


async def test_get_hourly_forecast_is_cached(respx_mock, hourly_forecast_data):
    route = respx_mock.get(url__startswith=FORECAST_URL).mock(
        return_value=httpx.Response(200, json=hourly_forecast_data)
    )
    first = await get_hourly_forecast(51.5, -0.12)
    second = await get_hourly_forecast(51.5, -0.12)

    assert route.call_count == 1
    assert second is first


async def test_get_hourly_forecast_caches_each_hours_value_separately(
    respx_mock, hourly_forecast_data
):
    route = respx_mock.get(url__startswith=FORECAST_URL).mock(
        return_value=httpx.Response(200, json=hourly_forecast_data)
    )
    await get_hourly_forecast(51.5, -0.12, hours=3)
    await get_hourly_forecast(51.5, -0.12, hours=24)

    assert route.call_count == 2


async def test_get_current_weather_is_cached(respx_mock, current_weather_data):
    route = respx_mock.get(url__startswith=FORECAST_URL).mock(
        return_value=httpx.Response(200, json=current_weather_data)
    )
    first = await get_current_weather(51.24, -0.58)
    second = await get_current_weather(51.24, -0.58)

    assert route.call_count == 1
    assert second is first


async def test_get_current_weather_raises_on_server_error(respx_mock):
    respx_mock.get(url__startswith=FORECAST_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        await get_current_weather(51.24, -0.58)
