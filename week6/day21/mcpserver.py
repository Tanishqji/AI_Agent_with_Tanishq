from mcp.server.mcpserver import MCPServer

mcp = MCPServer("Calculator")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers and return the sum."""
    return a + b + 100


if __name__ == "__main__":
    mcp.run(transport="stdio")