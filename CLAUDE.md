  # Project Overview

  **memories_webapp** is a web application for scrubbing through video content with keyframe-based playback. The app allows users to navigate through video timecode, with
   keyframes stored for improved scrubbing performance.

  ## Technical Stack

  - **Frontend**: Vanilla JavaScript with HTML/CSS
  - **Backend**: Python (FastAPI via `mcp_server.py`)
  - **Video Processing**: FFmpeg for keyframe extraction and normalization
  - **Client Integration**: MCP client for external system communication
  - **Main Entry**: `main.py` serves the web app

  ## Architecture

  main.py (web server)
  ├── client/ (frontend static files)
  │   ├── assets/
  │   └── uploads/
  ├── server/
  │   ├── mcp_client.py (MCP protocol client)
  │   └── mcp_server.py (MCP protocol server)
  └── main.py

  ## Key Technical Decisions

  ### Video Processing Pipeline
  1. **Keyframe Extraction**: Keyframes are extracted using FFmpeg and stored for better scrubbing
  2. **Normalization**: Video normalization function is available (see `c32d810`) for consistent playback
  3. **Scrubbing**: Keyframes enable smooth navigation through video timeline

  ### FFmpeg Usage
  - Command-line tool for video manipulation
  - Keyframe extraction for timecode navigation
  - Path handling requires careful consideration (see `9e403a7`)

  ### Project Structure
  - **Client-side**: Static files in `client/` directory
  - **Server-side**: MCP integration in `server/` directory
  - **Main entry point**: `main.py` serves the web interface

  ## Code Guidelines

  ### Frontend
  - Use vanilla JavaScript where possible
  - Keep client files in `client/` directory
  - Assets go in `client/assets/`
  - Uploaded content in `client/uploads/`

  ### Backend (Python)
  - Use FastAPI for API endpoints
  - Keep MCP logic in `mcp_client.py` and `mcp_server.py`
  - Handle video processing paths carefully
  - Follow the existing pattern of keeping client/server separation

  ### Video Processing
  - Always validate video paths before processing
  - Use keyframes for scrubbing operations
  - Normalize video output for consistent playback
  - Handle errors gracefully in the video processing pipeline

  ### File Naming
  - Use lowercase with hyphens for consistency
  - Video-related files should include timecode or keyframe info
  - Asset files should be prefixed appropriately

  ## Common Patterns

  ### FFmpeg Command Structure
  ```bash
  ffmpeg -i input -ss {time} -frames:v 1 keyframe.jpg

  Keyframe Storage

  - Store keyframes in a dedicated directory
  - Use consistent naming convention (e.g., video_id_timestamp.jpg)
  - Index keyframes for fast lookup

  Error Handling

  - Always validate input video paths
  - Check for existing uploads before processing
  - Provide user-friendly error messages

  Recent Changes

  Feature Development

  - Scrubbing Enhancement: Keyframes added for better timecode navigation (commit 5a8aae2)
  - Clear Function: Now pauses and clears video source before clearing (commit 1addba9)
  - Normalization: Function added for consistent video output (commit c32d810)
  - Path Fixes: FFmpeg path handling improved (commit 9e403a7)
  - FFmpeg Runner: Updated and vlog decisions made (commit 13d824b)

  External Systems

  - Linear: Track bugs and pipeline issues
  - Grafana: Monitor API latency and oncall dashboards (if applicable)
  - Git: Use git for version control and change tracking

  Debugging Tips

  1. Check FFmpeg installation and paths
  2. Verify video file accessibility
  3. Monitor keyframe generation logs
  4. Check upload directory permissions
  5. Validate MCP client-server communication

  Testing Checklist

  - Video upload works correctly
  - Keyframe extraction runs without errors
  - Scrubbing navigation is smooth
  - Clear button pauses and clears properly
  - Normalization output is consistent
  - MCP connections are stable
  - Error messages are user-friendly

  Performance Considerations

  - Process keyframes asynchronously when possible
  - Cache frequently accessed video data
  - Stream video instead of loading entire files
  - Implement proper cleanup for uploaded content