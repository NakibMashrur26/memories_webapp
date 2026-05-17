# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

**memories_webapp** is a local-first AI-powered vlog generator that stitches video clips into a final vlog using:
- **Frontend**: Vanilla JS/HTML served statically
- **Backend**: FastAPI Python server (port 8000)
- **LLM**: Ollama (phi3:mini model for editing decisions)
- **Video Processing**: FFmpeg for stitching, scaling, filtering

### Request Flow

1. User uploads clips via web UI → stored in `uploads/`
2. User triggers `/stitch` endpoint
3. Server collects all clips from `uploads/`
4. `ollama_client.get_clip_metadata()` extracts ffprobe data (duration, size, resolution)
5. `ollama_client.generate_vlog_decisions()` calls Ollama to get editing decisions
6. `ffmpeg_runner.build_ffmpeg_command()` builds concat-based ffmpeg command
7. `ffmpeg_runner.run_ffmpeg()` executes and produces output in `outputs/`
8. `/clear` auto-deletes uploads and outputs
9. `/download` serves the final vlog

### Key Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app with endpoints (`/upload`, `/stitch`, `/download`, `/clear`) |
| `ollama_client.py` | Ollama integration - gets clip metadata and editing decisions |
| `ffmpeg_runner.py` | FFmpeg command builder and executor |
| `client/index.html` | Frontend UI (upload drag-drop, style selection, download) |
| `server/mcp_client.py` | MCP protocol client (currently minimal, see `main.py` import) |
| `server/mcp_server.py` | MCP protocol server (currently minimal) |
| `Dockerfile` | FastAPI + ffmpeg container |
| `docker-compose.yml` | Wires FastAPI + Ollama + Nginx |
| `nginx.conf` | Reverse proxy config (port 80 → port 8000) |
| `requirements.txt` | Python dependencies |

## Common Development Tasks

### Start the app

```bash
docker compose up
```

### Pull the model (first run only)

```bash
docker compose exec ollama ollama pull phi3:mini
```

### Run app without Docker (local dev)

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Test `/upload` endpoint

```bash
curl -X POST -F "file=@/path/to/video.mp4" http://localhost:8000/upload
```

### Test `/stitch` endpoint

```bash
curl "http://localhost:8000/stitch?name=myvlog&style=youtube"
```

### Test `/download` endpoint

```bash
curl http://localhost:8000/download
```

### Clear uploads and outputs

```bash
curl -X POST http://localhost:8000/clear
```

### Run a single test

Tests are in `tests/` directory (if present). Run with:

```bash
pytest tests/ -v
```

Run a specific test:

```bash
pytest tests/test_ollama_client.py::test_generate_decisions -v
```

### Debug FFmpeg errors

Check `ffmpeg_runner.py:run_ffmpeg()` - it captures stderr. Add `print(result.stderr)` to see detailed errors.

Common issues:
- Missing input file paths in concat.txt
- Resolution not supported by source
- Audio codec mismatch

## Code Guidelines

### Video Processing

- Always validate video paths before processing
- Use keyframes for scrubbing operations (if implemented)
- Normalize video output for consistent playback (when implemented)
- FFmpeg path handling requires using absolute paths or relative to working directory

### File Naming

- Use lowercase with hyphens for consistency
- Video-related files should include timecode or keyframe info
- Asset files should be prefixed appropriately

### Error Handling

- Always validate input video paths
- Check for existing uploads before processing
- Provide user-friendly error messages
- Handle Pydantic validation errors from Ollama gracefully

### FFmpeg Command Structure

See `ffmpeg_runner.py:build_ffmpeg_command()` for the pattern:

1. Write concat file to `uploads/concat.txt` with `file` and optional `duration` lines
2. Apply filters: scale, pad, fade, audio normalization
3. Output with `-c:v libx264 -c:a aac -crf {crf} -preset {preset}`
4. Use `-g 30 -keyint_min 30` for keyframe intervals (scrubbing)

### Ollama Prompt Design

See `ollama_client.py:generate_vlog_decisions()` for the current prompt pattern:

- Pass clip metadata (duration, resolution, size, chronological order)
- Return Pydantic model for structured decisions
- Validate JSON output with `VlogDecisions.model_json_schema()`

### Frontend Guidelines

- Use vanilla JavaScript where possible
- Keep client files in `client/` directory
- Assets go in `client/assets/`
- Uploaded content in `client/uploads/`

## Important Notes

### Safari Download Issue

Safari ignores the `download` attribute on anchor tags for same-origin URLs. The fix is in `/download` endpoint with `Content-Disposition` header.

### MCP Server Status

Currently `server/mcp_client.py` and `server/mcp_server.py` are minimal stubs. The current implementation uses direct Ollama calls in `ollama_client.py`. If you add MCP integration:

1. Build tools in `mcp_server.py` (see `NOTES.md` for potential tools)
2. Wire up `mcp_client.py` to call tools
3. Have `generate_vlog_decisions` use MCP tools instead of direct prompts

### Performance

- Process keyframes asynchronously when possible
- Cache frequently accessed video data
- Stream video instead of loading entire files

### Testing Checklist

- [ ] Video upload works correctly
- [ ] Keyframe extraction runs without errors
- [ ] Scrubbing navigation is smooth
- [ ] Clear button pauses and clears properly
- [ ] Normalization output is consistent
- [ ] MCP connections are stable
- [ ] Error messages are user-friendly

### Privacy

Everything runs locally on your machine. Your videos never leave your device.

### Known Issues

- Safari download attribute is ignored for same-origin URLs (fixed via Content-Disposition header)
- Safari vlog naming doesn't work (low priority)

## Models

- **phi3:mini**: Current model - fast, lightweight, reliable JSON output
- **codellama**: Abandoned - generated invalid ffmpeg commands
- **llava-phi3**: Parked - vision capable but too complex

## Future Work

See `NOTES.md` for roadmap items:
- Nginx + HTTPS in production
- CI/CD with GitHub Actions
- Infrastructure as Code with Terraform
- iOS app (SwiftUI)
- Frame analysis with vision models
- Progress bar during stitching
- Background music support
- Title card overlays
