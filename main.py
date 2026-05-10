from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil

from mcp_client import generate_vlog_decisions
from ffmpeg_runner import build_ffmpeg_command, run_ffmpeg

app = FastAPI()

# Folders
UPLOADS_DIR = Path("uploads")
OUTPUTS_DIR = Path("outputs")
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# Serve static files (our frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return {"message": "Memories is here! Visit /upload to upload a video."}


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    destination = UPLOADS_DIR / file.filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "status": "uploaded"}


@app.post("/stitch")
async def stitch_videos(name: str = "vlog"):
    print(">>> stitch endpoint hit")
    filenames = sorted([
        f.name for f in UPLOADS_DIR.iterdir()
        if f.suffix.lower() in [".mp4", ".mov", ".m4v", ".avi"]
    ])

    if len(filenames) == 0:
        return {"error": "No videos found in uploads folder"}

    for file in OUTPUTS_DIR.iterdir():
        if file.is_file():
            file.unlink()

    # Get decisions and metadata via MCP
    plan = await generate_vlog_decisions(filenames)
    decisions = plan.decisions
    metadata = plan.metadata

    print(f">>> decisions: {decisions}")
    print(f">>> metadata: {metadata}")

    output_filename = f"{name}.mp4"
    command = build_ffmpeg_command(filenames, output_filename, decisions, metadata)
    print(f">>> ffmpeg command: {command}")

    success, message = run_ffmpeg(command)

    for file in UPLOADS_DIR.iterdir():
        if file.is_file():
            file.unlink()

    if success:
        return {
            "status": "success",
            "output_filename": output_filename,
            "decisions": decisions.model_dump(),
        }
    else:
        return {
            "status": "error",
            "message": message,
            "decisions": decisions.model_dump(),
        }


@app.post("/clear")
def clear_files():
    for folder in [UPLOADS_DIR, OUTPUTS_DIR]:
        for file in folder.iterdir():
            if file.is_file():
                file.unlink()
    return {"status": "cleared"}


@app.get("/download")
async def download_vlog():
    files = list(OUTPUTS_DIR.glob("*.mp4"))
    if not files:
        return {"error": "No vlog found, run /stitch first"}
    return FileResponse(
        path=files[0],
        media_type="video/mp4",
        filename=files[0].name,
    )