import httpx
from commute_mcp.models import CurrentWeather, HourlyForecast
from datetime import datetime

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

async def get_current_weather(latitude: float, longitude: float) -> CurrentWeather:

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "timezone": "Europe/London",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(FORECAST_URL, params=params)
        response.raise_for_status()

    return parse_current_weather(response.json())


async def get_hourly_forecast(latitude: float, longitude: float) -> list[HourlyForecast]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m",
        "timezone": "Europe/London",
        "forecast_days": 2, # train arriving at midnight covered
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(FORECAST_URL, params=params)
        response.raise_for_status()

    return parse_hourly_forecast(response.json())


def describe_weather_code(code: int) -> str:
    if code == 0:
        return "Clear sky"
    if code <= 2:
        return "Partly cloudy"
    if code == 3:
        return "Overcast"
    if code <= 48:
        return "Fog"
    if code <= 57:
        return "Drizzle"
    if code <= 67:
        return "Rain"
    if code <= 77:
        return "Snow"
    if code <= 82:
        return "Rain showers"
    if code <= 86:
        return "Snow showers"
    return "Thunderstorm"


def parse_current_weather(data: dict) -> CurrentWeather:
    current = data.get("current")
    if not current:
        raise ValueError("Weather data is missing the 'current' section.")

    return CurrentWeather(
        time=datetime.fromisoformat(current["time"]),
        conditions=describe_weather_code(current["weather_code"]),
        temperature_c=float(current["temperature_2m"]),
        feels_like_c=float(current["apparent_temperature"]),
        precipitation_mm=float(current["precipitation"]),
        wind_speed_kmh=float(current["wind_speed_10m"]),
    )


def parse_hourly_forecast(data: dict) -> list[HourlyForecast]:
    hourly = data.get("hourly")
    if not hourly:
        raise ValueError("Weather data is missing the 'hourly' section.")

    rows = zip(
        hourly["time"],
        hourly["weather_code"],
        hourly["temperature_2m"],
        hourly["precipitation_probability"],
        hourly["precipitation"],
        hourly["wind_speed_10m"],
        strict=True,
    )

    forecast = []
    for time, code, temp, rain_chance, rain_mm, wind in rows:
        forecast.append(
            HourlyForecast(
                time=datetime.fromisoformat(time),
                conditions=describe_weather_code(code),
                temperature_c=float(temp),
                precipitation_probability=int(rain_chance),
                precipitation_mm=float(rain_mm),
                wind_speed_kmh=float(wind),
            )
        )

    return forecast


if __name__ == "__main__":
    import asyncio

    forecast = asyncio.run(get_hourly_forecast(53.48, -2.24))
    print(len(forecast))
    print(forecast[0])
