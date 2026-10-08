from mcp.server.mcpserver import MCPServer

mcp = MCPServer("commute-mcp")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbenmbiuhuhrs together."""
    return a + b


if __name__ == "__main__":
    mcp.run()
