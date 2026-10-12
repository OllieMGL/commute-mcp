from dataclasses import asdict

import httpx
from mcp.server.mcpserver import MCPServer

from commute_mcp.stations import find_stations as search_stations
from commute_mcp.weather import get_current_weather, get_hourly_forecast
from commute_mcp.rail import MissingApiKeyError, get_departure_board

mcp = MCPServer("commute-mcp")

@mcp.tool()
async def get_weather(station: str) -> dict:
    """Get the current weather at a UK railway station.

    Args:
        station: The station name, for example "Guildford" or "London Waterloo".
    """
    matches = search_stations(station, limit=1)
    if not matches:
        return {"error": f"No station found matching '{station}'."}

    match = matches[0]
    try:
        weather = await get_current_weather(float(match["lat"]), float(match["long"]))
    except (httpx.HTTPError, ValueError):
        return {"error": "Could not get the weather from Open-Meteo. Try again shortly."}

    return {"station": match["stationName"], "weather": weather}

@mcp.tool()
def find_stations(query: str, limit: int = 5) -> list[dict]:
    """Search for UK railway stations by name.

    Use this to find a station's exact name and three-letter CRS code,
    or to check which station the user means when a name is ambiguous.

    Args:
        query: All or part of a station name, for example "Waterloo".
        limit: The maximum number of matches to return.
    """
    results = []
    for station in search_stations(query, limit=limit):
        results.append({"name": station["stationName"], "crs": station["crsCode"]})
    return results

@mcp.tool()
async def get_departures(station: str, destination: str | None = None, limit: int = 10) -> dict:
    """Get the next trains leaving a UK railway station.

    Also returns any disruption messages for the station, such as
    engineering works or rail replacement buses.

    Args:
        station: The station name, for example "Guildford" or "London Waterloo".
        destination: Optional. Only show trains that call at this station,
            for example "London Waterloo".
        limit: The maximum number of trains to return.
    """
    matches = search_stations(station, limit=1)
    if not matches:
        return {"error": f"No station found matching '{station}'."}

    match = matches[0]

    destination_crs = None # means it always exists even if nothing passed in
    destination_name = None # tracks the name of station it is matched to 
    if destination:
        destination_matches = search_stations(destination, limit=1)
        if not destination_matches:
            return {"error": f"No station found matching '{destination}'."}
        destination_crs = destination_matches[0]["crsCode"]
        destination_name = destination_matches[0]["stationName"]

    try:
        board = await get_departure_board(match["crsCode"], destination_crs=destination_crs, limit=limit)
    except MissingApiKeyError as error:
        return {"error": str(error)}
    except httpx.HTTPError as error:
        return {"error": f"Could not get departures from National Rail: {error}"}

    result = asdict(board)
    result["destination"] = destination_name
    return result

@mcp.tool()
async def plan_journey(origin: str, destination: str, limit: int = 5) -> dict:
    """Plan a train journey and check the weather at the destination.

    Returns the next direct trains from origin that call at destination,
    each with its scheduled and expected arrival time at the destination,
    plus the hourly forecast there for the next few hours. Use each
    train's arrival time to pick the matching forecast hour.

    For journeys that need a change, call this once per leg (for example
    Weybridge to Woking, then Woking to Guildford) and choose a second-leg
    train that leaves after the first train arrives.

    Args:
        origin: The station the user is leaving from, for example "Guildford".
        destination: The station the user is travelling to, for example "London Waterloo".
        limit: The maximum number of trains to return.
    """
    result = await get_departures(origin, destination, limit)
    if "error" in result:
        return result

    station = search_stations(destination, limit=1)[0]
    try:
        forecast = await get_hourly_forecast(float(station["lat"]), float(station["long"]), hours=3)
    except httpx.HTTPError:
        result["destination_forecast"] = None
        result["forecast_error"] = "Could not get the weather forecast."
        return result

    hours = []
    for hour in forecast:
        hours.append(asdict(hour))
    result["destination_forecast"] = hours

    return result





if __name__ == "__main__":
    mcp.run()