import subprocess
from pathlib import Path

RESOLUTION_MAP = {
    "720p": "1280:720",
    "1080p": "1920:1080",
    "4k": "3840:2160",
}


def build_ffmpeg_command(
    filenames: list[str],
    output_filename: str,
    decisions,
    metadata: list[dict],
) -> str:
    trim = decisions.trim_each_clip
    trim_secs = decisions.trim_seconds
    fade_in = decisions.add_fade_in
    fade_out = decisions.add_fade_out
    output_resolution = getattr(decisions, "output_resolution", "1080p")
    audio_normalize = getattr(decisions, "audio_normalize", False)

    # Calculate total duration ourselves — don't trust Ollama for this
    total_duration = 0.0
    for i, name in enumerate(filenames):
        clip_meta = next((c for c in metadata if c["index"] == i), None)
        if clip_meta:
            duration = clip_meta["duration_seconds"]
            total_duration += min(duration, trim_secs) if trim and trim_secs > 0 else duration

    fade_out_start = round(total_duration - 1, 1)

    # Write concat file in original order
    concat_path = Path("uploads/concat.txt")
    with concat_path.open("w") as f:
        for i, name in enumerate(filenames):
            clip_meta = next((c for c in metadata if c["index"] == i), None)
            clip_duration = clip_meta["duration_seconds"] if clip_meta else 999

            f.write(f"file '/{name}'\n")
            if trim and trim_secs > 0 and clip_duration > trim_secs:
                f.write(f"duration {trim_secs}\n")

    # Build video filters
    filters = []
    audio_filters = []

    # Scale to output resolution
    scale = RESOLUTION_MAP.get(output_resolution, "1920:1080")
    filters.append(f"scale={scale}:force_original_aspect_ratio=decrease")
    filters.append(f"pad={scale}:(ow-iw)/2:(oh-ih)/2")

    if fade_in:
        filters.append("fade=t=in:st=0:d=1")

    if fade_out and fade_out_start > 1:
        filters.append(f"fade=t=out:st={fade_out_start}:d=1")

    # Build audio filters
    if audio_normalize:
        audio_filters.append("loudnorm")

    filter_str = ""
    if filters and audio_filters:
        filter_str = f'-vf "{",".join(filters)}" -af "{",".join(audio_filters)}"'
    elif filters:
        filter_str = f'-vf "{",".join(filters)}"'
    elif audio_filters:
        filter_str = f'-af "{",".join(audio_filters)}"'

    command = (
        f"ffmpeg -y -f concat -safe 0 "
        f"-i uploads/concat.txt "
        f"-c:v libx264 -c:a aac "
        f"-movflags +faststart "
        f"{filter_str} "
        f"outputs/{output_filename}"
    )

    return command.strip()


def run_ffmpeg(command: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return True, "Success"
        else:
            return False, result.stderr

    except Exception as e:
        return False, str(e)
    

def normalize_clips(filenames: list[str]) -> list[str]:
    norm_dir = Path("uploads/normalized")
    norm_dir.mkdir(exist_ok=True)
    normalized = []

    for name in filenames:
        input_path = Path("uploads") / name
        output_path = norm_dir / f"{Path(name).stem}.mp4"

        print(f">>> normalizing {name}")
        result = subprocess.run(
            f'ffmpeg -y -i "{input_path}" '
            f'-c:v libx264 -c:a aac '
            f'-ac 2 -ar 44100 '
            f'"{output_path}"',
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            normalized.append(output_path.name)
        else:
            print(f">>> failed to normalize {name}: {result.stderr[-200:]}")

    return normalized