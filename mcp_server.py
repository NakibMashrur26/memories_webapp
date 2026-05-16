from mcp.server.fastmcp import FastMCP
from pathlib import Path
import subprocess
import json

mcp = FastMCP("Memories")

UPLOADS_DIR = Path("uploads")


@mcp.tool()
def get_available_styles() -> dict:
    """Returns available vlog editing styles with descriptions."""
    return {
        "cinematic": {
            "description": "Slow fades, high quality encoding, audio normalization. Best for travel vlogs and dramatic content.",
            "fade_in": "2 second fade in",
            "fade_out": "2 second fade out",
            "quality": "High (CRF 18)",
        },
        "youtube": {
            "description": "Fast cuts, energetic feel, audio normalization. Best for action, lifestyle or tutorial content.",
            "fade_in": "0.5 second fade in",
            "fade_out": "1 second fade out",
            "quality": "Standard (CRF 23)",
        },
        "homevideo": {
            "description": "Clean cuts, no effects, fast encoding. Best for family memories and casual recordings.",
            "fade_in": "None",
            "fade_out": "None",
            "quality": "Standard (CRF 23)",
        },
    }


@mcp.tool()
def get_all_metadata() -> list[dict]:
    """Returns metadata for all clips in the uploads folder."""
    clips = sorted([
        f.name for f in UPLOADS_DIR.iterdir()
        if f.suffix.lower() in [".mp4", ".mov", ".m4v", ".avi"]
    ])
    results = []
    for i, name in enumerate(clips):
        result = subprocess.run(
            f"ffprobe -v error -show_entries format=duration,size "
            f"-show_entries stream=width,height "
            f"-of json uploads/{name}",
            shell=True,
            capture_output=True,
            text=True,
        )
        try:
            info = json.loads(result.stdout)
            fmt = info.get("format", {})
            streams = info.get("streams", [{}])
            results.append({
                "index": i,
                "filename": name,
                "duration_seconds": round(float(fmt.get("duration", 0)), 1),
                "size_mb": round(int(fmt.get("size", 0)) / 1024 / 1024, 1),
                "width": streams[0].get("width", "unknown"),
                "height": streams[0].get("height", "unknown"),
            })
        except:
            results.append({
                "index": i,
                "filename": name,
                "duration_seconds": 0.0,
                "size_mb": 0.0,
                "width": "unknown",
                "height": "unknown",
            })
    return results


@mcp.tool()
def get_clip_list() -> list[str]:
    """Returns a list of all video clips available for editing."""
    clips = [
        f.name for f in UPLOADS_DIR.iterdir()
        if f.suffix.lower() in [".mp4", ".mov", ".m4v", ".avi"]
    ]
    return sorted(clips)


@mcp.tool()
def get_clip_metadata(filename: str) -> dict:
    """Returns metadata for a specific clip including duration, size, and resolution."""
    result = subprocess.run(
        f"ffprobe -v error -show_entries format=duration,size "
        f"-show_entries stream=width,height "
        f"-of json uploads/{filename}",
        shell=True,
        capture_output=True,
        text=True,
    )
    try:
        info = json.loads(result.stdout)
        fmt = info.get("format", {})
        streams = info.get("streams", [{}])
        return {
            "filename": filename,
            "duration_seconds": round(float(fmt.get("duration", 0)), 1),
            "size_mb": round(int(fmt.get("size", 0)) / 1024 / 1024, 1),
            "width": streams[0].get("width", "unknown"),
            "height": streams[0].get("height", "unknown"),
        }
    except:
        return {"filename": filename, "error": "could not read metadata"}


@mcp.tool()
def get_total_duration() -> float:
    """Returns the total duration in seconds of all clips combined."""
    clips = [
        f.name for f in UPLOADS_DIR.iterdir()
        if f.suffix.lower() in [".mp4", ".mov", ".m4v", ".avi"]
    ]
    total = 0.0
    for name in clips:
        result = subprocess.run(
            f"ffprobe -v error -show_entries format=duration "
            f"-of json uploads/{name}",
            shell=True,
            capture_output=True,
            text=True,
        )
        try:
            info = json.loads(result.stdout)
            total += float(info["format"]["duration"])
        except:
            pass
    return round(total, 1)


@mcp.tool()
def get_shortest_clip() -> dict:
    """Returns the filename and duration of the shortest clip."""
    clips = [
        f.name for f in UPLOADS_DIR.iterdir()
        if f.suffix.lower() in [".mp4", ".mov", ".m4v", ".avi"]
    ]
    shortest = None
    shortest_duration = float("inf")

    for name in clips:
        result = subprocess.run(
            f"ffprobe -v error -show_entries format=duration "
            f"-of json uploads/{name}",
            shell=True,
            capture_output=True,
            text=True,
        )
        try:
            info = json.loads(result.stdout)
            duration = float(info["format"]["duration"])
            if duration < shortest_duration:
                shortest_duration = duration
                shortest = name
        except:
            pass

    return {"filename": shortest, "duration_seconds": round(shortest_duration, 1)}


@mcp.tool()
def get_available_resolutions() -> list[str]:
    """Returns available output resolutions."""
    return ["720p", "1080p", "4k"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=8050)