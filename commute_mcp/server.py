from dataclasses import asdict

import httpx
from mcp.server.mcpserver import MCPServer

from commute_mcp.stations import find_stations as search_stations
from commute_mcp.weather import get_current_weather, get_hourly_forecast, hours_until
from commute_mcp.rail import MissingApiKeyError, get_departure_board

mcp = MCPServer("commute-mcp")

def resolve_station(query: str) -> tuple[dict | None, str | None]:
    """Find the best station for a name, plus a note if the match was a guess."""
    matches = search_stations(query, limit=5)
    if not matches:
        return None, None

    wanted = query.lower().strip()
    for station in matches:
        if station["stationName"].lower() == wanted:
            return station, None  # exact name, no guessing needed

    best = matches[0]
    if wanted not in best["stationName"].lower():
        return best, f"No station called '{query}'; using the closest match, {best['stationName']}."

    if len(matches) > 1:
        others = []
        for station in matches[1:]:
            others.append(station["stationName"])
        return best, f"Assumed {best['stationName']}. Other matches: {', '.join(others)}."

    return best, None

@mcp.tool()
async def get_weather(station: str) -> dict:
    """Get the current weather at a UK railway station.

    If a station name was ambiguous or misspelt, "notes" says which
    station was used. Tell the user, so they can correct it if needed.

    Args:
        station: The station name, for example "Guildford" or "London Waterloo".
    """
    match, note = resolve_station(station)
    if match is None:
        return {"error": f"No station found matching '{station}'."}

    try:
        weather = await get_current_weather(float(match["lat"]), float(match["long"]))
    except (httpx.HTTPError, ValueError):
        return {"error": "Could not get the weather from Open-Meteo. Try again shortly."}

    notes = []
    if note:
        notes.append(note)
    return {"station": match["stationName"], "weather": weather, "notes": notes}

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

    If a station name was ambiguous or misspelt, "notes" says which
    station was used. Tell the user, so they can correct it if needed.

    Args:
        station: The station name, for example "Guildford" or "London Waterloo".
        destination: Optional. Only show trains that call at this station,
            for example "London Waterloo".
        limit: The maximum number of trains to return.
    """
    notes = []
    match, note = resolve_station(station)
    if match is None:
        return {"error": f"No station found matching '{station}'."}
    if note:
        notes.append(note)

    destination_crs = None # means it always exists even if nothing passed in
    destination_name = None # tracks the name of station it is matched to
    if destination:
        destination_match, note = resolve_station(destination)
        if destination_match is None:
            return {"error": f"No station found matching '{destination}'."}
        if note:
            notes.append(note)
        destination_crs = destination_match["crsCode"]
        destination_name = destination_match["stationName"]

    try:
        board = await get_departure_board(match["crsCode"], destination_crs=destination_crs, limit=limit)
    except MissingApiKeyError as error:
        return {"error": str(error)}
    except httpx.HTTPError as error:
        return {"error": f"Could not get departures from National Rail: {error}"}

    result = asdict(board)
    result["destination"] = destination_name
    result["notes"] = notes
    return result

@mcp.tool()
async def plan_journey(origin: str, destination: str, limit: int = 5) -> dict:
    """Plan a train journey and check the weather at the destination.

    Returns the next direct trains from origin that call at destination,
    each with its scheduled and expected arrival time at the destination,
    plus the hourly forecast there from now until the last train arrives.
    Use each train's arrival time to pick the matching forecast hour.

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

    station, _ = resolve_station(destination)  # its note is already in result["notes"]
    try:
        forecast = await get_hourly_forecast(float(station["lat"]), float(station["long"]))
    except (httpx.HTTPError, ValueError):
        result["destination_forecast"] = None
        result["forecast_error"] = "Could not get the weather forecast."
        return result

    # Open-Meteo's first hour is the current UK hour, so use it as "now"
    start_hour = forecast[0].time.hour
    hours_needed = 1  # always include at least the current hour
    for departure in result["departures"]:
        arrival = departure["arrival_expected"]
        if not arrival or ":" not in arrival:  # "On time", "Delayed" or missing
            arrival = departure["arrival_scheduled"]
        if arrival:
            hours_needed = max(hours_needed, hours_until(start_hour, arrival))

    hours = []
    for hour in forecast[:hours_needed]:
        hours.append(asdict(hour))
    result["destination_forecast"] = hours

    return result

if __name__ == "__main__":
    mcp.run()