from mcp.server.fastmcp import FastMCP
from pathlib import Path
import subprocess
import json

mcp = FastMCP("Memories")

UPLOADS_DIR = Path("uploads")

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
def get_editing_guidelines() -> dict:
    """Returns valid editing parameters and constraints for this vlog editor."""
    return {
        "trim_seconds": {
            "description": "Maximum seconds to KEEP from each clip",
            "minimum": 3.0,
            "tip": "Must be greater than shortest clip duration. 0 means keep full clip. Never set below 3.0."
        },
        "trim_each_clip": {
            "description": "Whether to trim clips to trim_seconds length",
            "tip": "Set to true if any clip is significantly longer than others"
        },
        "add_fade_in": {
            "description": "Fade in from black at the start of the vlog",
            "tip": "true for cinematic feel"
        },
        "add_fade_out": {
            "description": "Fade out to black at the end of the vlog",
            "tip": "true for cinematic feel"
        },
        "constraints": [
            "trim_seconds must be at least 3.0",
            "trim_seconds 0 means keep full clip, do not trim",
            "trim_seconds must never be less than the shortest clip duration",
            "all clips play at normal speed, do not change speed",
            "do not reorder clips"
        ]
    }


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
def get_available_transitions() -> list[str]:
    """Returns available transition types between clips."""
    return ["cut", "crossfade"]

@mcp.tool()
def get_available_resolutions() -> list[str]:
    """Returns available output resolutions."""
    return ["720p", "1080p", "4k"]

@mcp.tool()
def get_ffmpeg_capabilities() -> dict:
    """Returns available ffmpeg filters, codecs and options for vlog editing."""
    return {
        "video_filters": {
            "scale": "Resize video. Example: scale=1920:1080",
            "fade": "Fade in/out. Example: fade=t=in:st=0:d=1",
            "xfade": "Crossfade between clips. Example: xfade=transition=fade:duration=1",
            "pad": "Add padding/letterbox. Example: pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "drawtext": "Text overlay. Example: drawtext=text='Hello':fontsize=48:fontcolor=white",
            "crop": "Crop video. Example: crop=1280:720",
            "setpts": "Change speed. Example: setpts=0.5*PTS for 2x speed",
        },
        "audio_filters": {
            "loudnorm": "Normalize audio levels",
            "volume": "Adjust volume. Example: volume=1.5",
            "afade": "Audio fade. Example: afade=t=in:st=0:d=1",
        },
        "codecs": {
            "video": "libx264 (H.264, most compatible)",
            "audio": "aac (most compatible)",
        },
        "tips": [
            "Always use -movflags +faststart for web playback",
            "Use -f concat -safe 0 -i concat.txt to stitch clips",
            "Clips are listed in uploads/concat.txt",
            "Output goes to outputs/filename.mp4",
            "Chain video filters with commas: -vf 'scale=1920:1080,fade=t=in:st=0:d=1'",
        ]
    }

@mcp.tool()
def validate_ffmpeg_command(command: str) -> dict:
    """Validates an ffmpeg command by doing a dry run without encoding."""
    result = subprocess.run(
        f"{command} -t 0 -f null -",
        shell=True,
        capture_output=True,
        text=True,
    )
    return {
        "valid": result.returncode == 0,
        "error": result.stderr[-500:] if result.returncode != 0 else None,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=8050)