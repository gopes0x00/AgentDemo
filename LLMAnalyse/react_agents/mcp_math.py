from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b : int) -> int:
    """Adds two integer values"""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiplies two integer values"""
    return a * b

@mcp.tool()
def divide(a: int, b: int) -> int:
    """Divides two integer values"""
    return a / b

@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtracts two integer values"""
    return a - b

if __name__ == "__main__":
    mcp.run(transport="stdio")