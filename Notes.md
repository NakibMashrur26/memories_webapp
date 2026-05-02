# Dev Notes

## Known Issues

### Safari Compatibility
- The `download` attribute on anchor tags is ignored in Safari for same-origin URLs
- Vlog naming works correctly in Chrome but not Safari
- Fix: set Content-Disposition header in /download endpoint
- `headers={"Content-Disposition": f"attachment; filename={files[0].name}"}`
- Low priority for now

---

## Future Milestones

### iOS App (v2)
- Backend (FastAPI + Ollama + ffmpeg) stays exactly as-is on Mac
- Replace index.html with a native SwiftUI iOS app
- iOS app talks to Mac backend over local WiFi
- Mac's local IP replaces 127.0.0.1 in the app's API calls
- Key challenge: iOS camera roll permissions for video access
- Key constraint: iPhone and Mac must be on same WiFi, or backend needs to be hosted
- Consider: hosting backend on a cheap server for anywhere access

---

## Deployment Plan

### Server Requirements
- 8GB+ RAM (Ollama needs it for codellama)
- Decent CPU (ffmpeg processing 4K clips is heavy)
- Sufficient storage (uploaded videos pile up fast)
- Linux (Ubuntu recommended)
- Open port 80/443

### Server Setup
```bash
# Install dependencies
sudo apt install python3 python3-pip ffmpeg nginx

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull codellama

# Clone repo
git clone https://github.com/you/ollamaPlayground.git
cd ollamaPlayground/memories
pip install -r requirements.txt
```

### Nginx Config
- Reverse proxy from port 80/443 to FastAPI on port 8000
- Set `client_max_body_size 500M` for large video uploads
- Config file at `/etc/nginx/sites-available/memories`

### HTTPS
- Free with Let's Encrypt via Certbot
- `sudo certbot --nginx -d memories.yourdomain.com`
- Auto-renews

### Keep App Running
- Use systemd service to auto-restart on crash
- Service file at `/etc/systemd/system/memories.service`
- `sudo systemctl enable memories && sudo systemctl start memories`

### Domain
- Buy a domain and create an A record pointing to server's public IP
- `memories.yourdomain.com → YOUR_SERVER_IP`

### Before Going Public
- Add authentication — no login means anyone can use your server
- Consider rate limiting uploads
- Consider auto-cleanup of old files on a schedule
- Consider a max file size limit on uploads