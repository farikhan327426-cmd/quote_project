import sys
from mcp.server.fastmcp import FastMCP
from src.tools.getprice_tool import test_connection, generate_quote

# Initialize FastMCP Server
mcp = FastMCP("Furniture Quote Server")

# Register Tools
mcp.tool(name="test_connection")(test_connection)
mcp.tool(name="generate_quote")(generate_quote)

if __name__ == "__main__":
    mcp.run()
