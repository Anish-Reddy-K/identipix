# Identipix

Self-hosted wrapper around a public Google Drive folder of event photos. The organizer pastes a folder link and gets an event link and QR. Guests take a selfie and see only the photos they appear in. Photos stay in Drive. We store only face embeddings and Drive file IDs. Selfies are processed in memory and never written to disk.

## Setup
1. Create a Google API key with Drive API v3 enabled (no OAuth).
2. Create a Cloudflare tunnel; point its public hostname to `http://app:8080`.
3. `cp .env.example .env` and fill in `GOOGLE_API_KEY`, `PUBLIC_BASE_URL`, `TUNNEL_TOKEN`.
4. `docker compose up -d --build`

HTTPS (from the tunnel) is required for camera access in browsers.

## Use
- Open `PUBLIC_BASE_URL`, paste the folder link (shared as "Anyone with the link"), click Create.
- Bookmark the admin page. It is the only way to manage the event. Share the event link or QR with guests.

## Develop
```
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python fastapi "uvicorn[standard]" opencv-python-headless numpy httpx python-multipart segno pytest
.venv/bin/python -m pytest
```
Models go in `models/` (the Dockerfile downloads them; for local runs download them from opencv_zoo, see Dockerfile for URLs).

## Tuning
`eval/eval.py` prints precision/recall per threshold: `python -m eval.eval eval/labels.json`.
Format: `{"folder_url": "...", "people": {"name": {"selfie": "path.jpg", "photos": ["file_id", ...]}}}`.

Models: YuNet (MIT) and SFace (Apache-2.0) from OpenCV Zoo. License: MIT.
