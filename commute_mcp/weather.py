import httpx

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


async def get_current_weather(latitude: float, longitude: float) -> dict: # returns the raw JSON as a dictionary
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "timezone": "Europe/London",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(FORECAST_URL, params=params)
        response.raise_for_status()

    return response.json()


if __name__ == "__main__":
    import asyncio

    print(asyncio.run(get_current_weather(53.48, -2.24)))