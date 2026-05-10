# mcp_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Memories")

@mcp.tool()
def get_total_duration() -> str:
    return "Tool is working"

if __name__ == "__main__":
    mcp.run()