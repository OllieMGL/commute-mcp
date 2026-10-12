import httpx
from commute_mcp.models import CurrentWeather, HourlyForecast
from datetime import datetime
from commute_mcp.cache import TTLCache

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_CACHE = TTLCache(900)  # weather changes slowly, so keep it for 15 minutes


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    51: "Drizzle",
    53: "Drizzle",
    55: "Drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain",
    71: "Snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy rain showers",
    85: "Snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with hail",
}

async def get_current_weather(latitude: float, longitude: float) -> CurrentWeather:

    key = ("current", latitude, longitude)
    cached = WEATHER_CACHE.get(key)
    if cached is not None:
        return cached

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "timezone": "Europe/London",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(FORECAST_URL, params=params)
        response.raise_for_status()

    weather = parse_current_weather(response.json())
    WEATHER_CACHE.set(key, weather)
    return weather

async def get_hourly_forecast(latitude: float, longitude: float, hours: int = 24) -> list[HourlyForecast]:

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m",
        "timezone": "Europe/London",
        "forecast_hours": hours,
    }

    key = ("hourly", latitude, longitude, hours)
    cached = WEATHER_CACHE.get(key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(FORECAST_URL, params=params)
        response.raise_for_status()

    forecast = parse_hourly_forecast(response.json())
    WEATHER_CACHE.set(key, forecast)
    return forecast



def describe_weather_code(code: int) -> str:
    return WEATHER_CODES.get(code, "Unknown")

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

    forecast = asyncio.run(get_hourly_forecast(51.50, -0.11, hours=3))
    for hour in forecast:
        print(hour)