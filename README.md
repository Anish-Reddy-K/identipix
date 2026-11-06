<h1 align="center">Identipix</h1>
<p align="center"><b>Photos that find you.</b><br>Guests take a selfie and see only the event photos they appear in. Free, open source, self-hosted.</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-D81B60"></a>
  <a href="https://github.com/Anish-Reddy-K/identipix-v2/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/Anish-Reddy-K/identipix-v2?style=flat&color=8E24AA"></a>
</p>

## Why

After an event, the photographer shares a folder with hundreds of photos. Nobody wants to scroll through all of them to find the five where they appear.

Identipix wraps a **public Google Drive folder**. The organizer pastes the link and gets an event link and a QR code. A guest opens it, takes a selfie, and sees only their photos, then saves them straight to their phone.

## How it works

1. **Organizer** pastes a Drive folder link. Identipix reads the photos once and stores a numeric "face fingerprint" for each face it finds (in our test, 132 photos took about 10 seconds on a Mac).
2. **Guest** opens the event link (or scans the QR) and takes a selfie. It is turned into a fingerprint in memory and compared with the event's fingerprints. A match takes well under a second.
3. **Results** show the photos they appear in, as "Found you" (confident) and "Might be you" (borderline). They tap a photo to open the original in Drive, or save it to their phone.

The organizer can also pick **Highlights** (venue, food, anything everyone should see) and guests always get a **View all photos** link to the full folder.

## Privacy by design

- **Selfies are never saved.** They are read into memory, matched, and discarded. Never written to disk, never logged.
- **Photos are not stored.** They stay in Google Drive. Only face fingerprints (128 numbers per face, not images) and Drive file IDs are kept.
- **Everything runs on your machine.** Face detection and matching run locally with OpenCV. No selfie or photo goes to an AI service.
- **No accounts, cookies or analytics.**
- **Events expire** after 30 days (configurable), and organizers can delete them any time.

Details: [Privacy Policy](legal/PRIVACY.md) and [Terms](legal/TERMS.md). Fingerprints are still biometric data, so tell guests face matching is used.

## Self-host in 5 minutes

You need Docker, a Google API key (Drive API v3 enabled, no OAuth) and a Cloudflare tunnel (HTTPS is required for camera access).

1. Create the key at [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and enable the Drive API.
2. Create a Cloudflare tunnel and point its public hostname to `http://app:8080`.
3. `cp .env.example .env`, then fill in `GOOGLE_API_KEY`, `PUBLIC_BASE_URL` and `TUNNEL_TOKEN`.
4. `docker compose up -d --build`

Open `PUBLIC_BASE_URL`, paste a folder shared as "Anyone with the link", and click **Create**. Bookmark the admin page: it is the only way to manage the event.

## Accuracy and limits

Face matching is not perfect. Look-alikes can slip into "Might be you", and poor light or odd angles can hide a photo. Tune `MATCH_THRESHOLD` and `STRONG_THRESHOLD` in `.env`, and measure with `python -m eval.eval eval/labels.json`, which prints precision and recall per threshold (format: `{"folder_url": "...", "people": {"name": {"selfie": "path.jpg", "photos": ["file_id"]}}}`).

Other limits: the Drive folder must be public by link, and the saved-to-phone copy is the large preview (up to 2048 px), not the original file.

## Tech

Python 3.12, FastAPI, OpenCV (YuNet detector + SFace recognizer), SQLite, vanilla HTML/CSS/JS with no build step. One process, one small database.

```
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python fastapi "uvicorn[standard]" opencv-python-headless numpy httpx python-multipart segno pytest
.venv/bin/python -m pytest
```

For local runs, download the two models into `models/` (URLs in the `Dockerfile`). The first test run downloads one sample photo into `tests/data/` (it shows real people, so it is not stored in this repo).

## Contributing

Issues and pull requests are welcome. If Identipix helped you, a star on GitHub helps others find it.

## Credits

Models: YuNet (MIT) and SFace (Apache-2.0) from OpenCV Zoo. Fonts: Bricolage Grotesque and Inter (SIL OFL), self-hosted. Soft (neumorphic) surfaces use the colours and shadows of Themesberg's [Neumorphism UI](https://github.com/themesberg/neumorphism-ui-bootstrap) (MIT). Social icons from [Simple Icons](https://simpleicons.org) (CC0).

MIT licensed. Made with love in Waterloo, Canada.
