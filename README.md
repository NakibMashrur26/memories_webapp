# 🎬 Memories

A local-first, AI-powered vlog generator. Upload your video clips, and Memories uses a local LLM (via Ollama) to make smart editing decisions, then stitches everything together with ffmpeg — all running on your own machine. No cloud, no subscriptions, no data leaving your device.

---

## How it works

```
Upload clips → Ollama analyzes metadata → ffmpeg stitches → Download vlog
```

1. Upload your video clips through the web UI
2. Ollama (running locally) analyzes clip durations and makes editing decisions
3. ffmpeg executes those decisions — trimming, fading, stitching
4. Download your finished vlog

---

## Stack

| Layer | Tool |
|---|---|
| Backend | FastAPI (Python) |
| LLM | Ollama + phi3:mini |
| Video processing | ffmpeg |
| Reverse proxy | Nginx |
| Containerization | Docker + Docker Compose |

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (6GB+ memory allocated)
- [Ollama](https://ollama.com) (handled inside Docker)
- A domain (for production deployment)

---

## Local Development

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/memories_webapp.git
cd memories_webapp
```

### 2. Start the app

```bash
docker compose up
```

This starts three services:
- **Nginx** on port 80
- **FastAPI** on port 8000 (internal)
- **Ollama** on port 11434 (internal)

### 3. Pull the model

On first run, pull the LLM model into the Ollama container:

```bash
docker compose exec ollama ollama pull phi3:mini
```

### 4. Open the app

Visit **http://localhost** in your browser.

---

## Usage

1. Open **http://localhost**
2. Drag and drop your video clips (MP4, MOV, M4V supported)
3. Give your vlog a name
4. Click **Create vlog**
5. Watch the video preview and download when ready

---

## Project Structure

```
memories_webapp/
├── main.py              # FastAPI app — routes and endpoints
├── ollama_client.py     # Ollama integration — LLM decisions
├── ffmpeg_runner.py     # ffmpeg execution — video stitching
├── static/
│   └── index.html       # Frontend UI
├── uploads/             # Temporary clip storage (auto-cleared)
├── outputs/             # Finished vlogs
├── Dockerfile           # FastAPI + ffmpeg container
├── docker-compose.yml   # Wires FastAPI + Ollama + Nginx
├── nginx.conf           # Nginx reverse proxy config
├── requirements.txt     # Python dependencies
└── NOTES.md             # Dev notes and future milestones
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Upload a video clip |
| `POST` | `/stitch?name=myvlog` | Stitch uploaded clips into a vlog |
| `GET` | `/download` | Download the finished vlog |
| `POST` | `/clear` | Clear uploads and outputs |

---

## How Ollama makes decisions

Ollama receives metadata about each clip (duration, resolution, file size) and returns structured editing decisions:

```json
{
    "trim_each_clip": true,
    "trim_seconds": 8.0,
    "add_fade_in": true,
    "add_fade_out": true,
    "speed": 1.0
}
```

These decisions are validated with Pydantic and passed to ffmpeg for execution. Ollama never touches the video files directly.

---

## Models tested

| Model | Status | Notes |
|---|---|---|
| `codellama` | ❌ Abandoned | Generated invalid ffmpeg commands |
| `llava-phi3` | ⚠️ Parked | Vision capable but too complex |
| `phi3:mini` | ✅ Current | Fast, lightweight, reliable JSON output |

---

## Roadmap

See [NOTES.md](./NOTES.md) for full details.

- [ ] Nginx + HTTPS in production
- [ ] CI/CD with GitHub Actions
- [ ] Infrastructure as Code with Terraform
- [ ] iOS app (SwiftUI frontend, Mac backend)
- [ ] Frame analysis with vision models
- [ ] Progress bar during stitching
- [ ] Background music support
- [ ] Title card overlays

---

## Privacy

Everything runs locally on your machine. Your videos never leave your device. No API keys, no cloud processing, no telemetry.

---

## License

MIT
