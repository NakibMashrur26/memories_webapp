import os
from ollama import Client
from pydantic import BaseModel
import subprocess
import json
import os

client = Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

class VlogDecisions(BaseModel):
    trim_each_clip: bool
    trim_seconds: float
    add_fade_in: bool
    add_fade_out: bool
    speed: float


def generate_vlog_decisions(filenames: list[str], metadata: list[dict]) -> VlogDecisions:
    clips_info = "\n".join(
        [
            f"- Clip {c['index']}: {c['filename']} | {c['duration_seconds']}s | {c['size_mb']}MB | {c['width']}x{c['height']}"
            for c in metadata
        ]
    )

    total_duration = sum(c.get("duration_seconds", 0) for c in metadata)
    shortest_clip = min(c.get("duration_seconds", 0) for c in metadata)

    birthtimes = {}
    for name in filenames:
        try:
            birthtimes[name] = os.stat(f"uploads/{name}").st_birthtime
        except:
            birthtimes[name] = 0

    chronological_order = sorted(range(len(filenames)), key=lambda i: birthtimes[filenames[i]])

    prompt = f"""
You are a professional vlog editor. Create a vlog from these video clips:
{clips_info}

Total duration: {round(total_duration, 1)} seconds
Shortest clip: {shortest_clip} seconds
Chronological order by creation time: {chronological_order}

Make editing decisions to create an engaging vlog. Consider pacing and flow.

Rules:
- trim_each_clip: true if any clip is over 15 seconds, otherwise false
- trim_seconds: if trimming, how many seconds to keep per clip. Must be at least {max(3.0, shortest_clip)}. Set to 0 if not trimming.
- add_fade_in: true for cinematic feel
- add_fade_out: true for cinematic feel
- speed: 1.0 for normal. Only change if total duration is over 3 minutes.
"""

    response = client.chat(
        model="phi3:mini",
        messages=[{"role": "user", "content": prompt}],
        format=VlogDecisions.model_json_schema(),
    )

    decisions = VlogDecisions.model_validate_json(response.message.content)
    print(f">>> Raw Ollama response: {decisions}")

    return decisions


def get_clip_metadata(filenames: list[str]) -> list[dict]:
    print(f">>> get_clip_metadata called with: {filenames}")
    clips = []
    for i, name in enumerate(filenames):
        result = subprocess.run(
            f"ffprobe -v error -show_entries format=duration,size,filename "
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
            clips.append(
                {
                    "index": i,
                    "filename": name,
                    "duration_seconds": round(float(fmt.get("duration", 0)), 1),
                    "size_mb": round(int(fmt.get("size", 0)) / 1024 / 1024, 1),
                    "width": streams[0].get("width", "unknown"),
                    "height": streams[0].get("height", "unknown"),
                }
            )
        except:
            clips.append({
                "index": i,
                "filename": name, 
                "duration_seconds": 0.0,
                "size_mb": 0.0,
                "width": "unknown",
                "height": "unknown",
            })

    return clips