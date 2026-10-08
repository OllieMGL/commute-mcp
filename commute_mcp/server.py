from mcp.server.mcpserver import MCPServer

from commute_mcp.weather import get_current_weather

mcp = MCPServer("commute-mcp")


@mcp.tool()
async def get_weather(latitude: float, longitude: float) -> dict:
    # doc string - ai reads it to understand what it does 
    """Get the current weather at a location.

    Args:
        latitude: Latitude in decimal degrees, for example 53.48 for Manchester.
        longitude: Longitude in decimal degrees, for example -2.24 for Manchester.
    """
    return await get_current_weather(latitude, longitude)


if __name__ == "__main__":
    mcp.run()