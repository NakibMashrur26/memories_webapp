import subprocess
from pathlib import Path

RESOLUTION_MAP = {
    "720p": "1280:720",
    "1080p": "1920:1080",
    "4k": "3840:2160",
}

STYLE_TEMPLATES = {
    "homevideo": {
        "crf": 23,
        "preset": "fast",
        "fade_in_duration": 0,
        "fade_out_duration": 0,
        "audio_normalize": False,
    },
    "youtube": {
        "crf": 23,
        "preset": "veryfast",
        "fade_in_duration": 0.5,
        "fade_out_duration": 1.0,
        "audio_normalize": True,
    },
    "cinematic": {
        "crf": 18,
        "preset": "slow",
        "fade_in_duration": 2.0,
        "fade_out_duration": 2.0,
        "audio_normalize": True,
    },
}


def build_ffmpeg_command(
    filenames: list[str],
    output_filename: str,
    decisions,
    metadata: list[dict],
) -> str:
    style = getattr(decisions, "style", "homevideo")
    trim = decisions.trim_each_clip
    trim_secs = decisions.trim_seconds
    output_resolution = getattr(decisions, "output_resolution", "1080p")

    # Get style template
    template = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["homevideo"])
    crf = template["crf"]
    preset = template["preset"]
    fade_in_duration = template["fade_in_duration"]
    fade_out_duration = template["fade_out_duration"]
    audio_normalize = template["audio_normalize"]

    # Write concat file using absolute paths
    # Skip clips shorter than trim_secs to avoid ffmpeg errors
    upload_path = Path("uploads").resolve()
    concat_path = Path("uploads/concat.txt")
    included_durations = []

    with concat_path.open("w") as f:
        for i, name in enumerate(filenames):
            clip_meta = next((c for c in metadata if c["index"] == i), None)
            clip_duration = clip_meta["duration_seconds"] if clip_meta else 999

            # Skip clips shorter than trim duration
            if trim and trim_secs > 0 and clip_duration < trim_secs:
                print(f">>> skipping {name} — too short ({clip_duration}s < {trim_secs}s)")
                continue

            f.write(f"file '{upload_path}/{name}'\n")
            if trim and trim_secs > 0 and clip_duration > trim_secs:
                f.write(f"duration {trim_secs}\n")
                included_durations.append(trim_secs)
            else:
                included_durations.append(clip_duration)

    # Calculate total duration from included clips only
    total_duration = sum(included_durations)
    fade_out_start = round(total_duration - fade_out_duration, 1)
    print(f">>> included {len(included_durations)} clips, total duration: {round(total_duration, 1)}s")

    # Build video filters
    filters = []
    audio_filters = []

    # Scale to output resolution
    scale = RESOLUTION_MAP.get(output_resolution, "1920:1080")
    filters.append(f"scale={scale}:force_original_aspect_ratio=decrease")
    filters.append(f"pad={scale}:(ow-iw)/2:(oh-ih)/2")

    if fade_in_duration > 0:
        filters.append(f"fade=t=in:st=0:d={fade_in_duration}")

    if fade_out_duration > 0 and fade_out_start > 0:
        filters.append(f"fade=t=out:st={fade_out_start}:d={fade_out_duration}")

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
        f"-crf {crf} -preset {preset} "
        f"-movflags +faststart "
        f"-g 30 -keyint_min 30 "
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
            print(f">>> ffmpeg error: {result.stderr}")
            return False, result.stderr

    except Exception as e:
        return False, str(e)


# Normalization — currently shelved, use when ready
# See NOTES.md for planned improvements
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