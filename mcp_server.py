from mcp.server.fastmcp import FastMCP
from pathlib import Path

mcp = FastMCP("Memories")

UPLOADS_DIR = Path("uploads")

@mcp.tool()
def get_clip_list() -> list[str]:
    """Returns a list of all video clips available for editing."""
    clips = [
        f.name for f in UPLOADS_DIR.iterdir()
        if f.suffix.lower() in [".mp4", ".mov", ".m4v", ".avi"]
    ]
    return sorted(clips)

if __name__ == "__main__":
    mcp.run()