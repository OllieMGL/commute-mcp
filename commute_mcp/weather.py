import httpx
from commute_mcp.models import CurrentWeather
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

if __name__ == "__main__":
    import asyncio

    print(asyncio.run(get_current_weather(53.48, -2.24)))