from mcp.server.mcpserver import MCPServer

from commute_mcp.stations import find_stations as search_stations
from commute_mcp.weather import get_current_weather

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
    weather = await get_current_weather(float(match["lat"]), float(match["long"]))
    
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



if __name__ == "__main__":
    mcp.run()