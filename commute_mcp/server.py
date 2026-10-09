from mcp.server.mcpserver import MCPServer
from commute_mcp.stations import find_stations

from commute_mcp.weather import get_current_weather

mcp = MCPServer("commute-mcp")


@mcp.tool()
async def get_weather(station: str) -> dict:
    """Get the current weather at a UK railway station.

    Args:
        station: The station name, for example "Guildford" or "London Waterloo".
    """
    matches = find_stations(station, limit=1)
    if not matches:
        return {"error": f"No station found matching '{station}'."}

    match = matches[0]
    weather = await get_current_weather(float(match["lat"]), float(match["long"]))
    
    return {"station": match["stationName"], "weather": weather}



if __name__ == "__main__":
    mcp.run()