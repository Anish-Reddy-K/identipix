# Identipix v1 — Build Spec

> **Core principle:** The best engineering is not the most complex solution. It is the simplest reliable system that fully solves the problem and is demonstrably correct.
> Do not add anything not in this spec. No frameworks, no extra services, no "nice to haves".

## 1. What it is

An open-source, self-hosted wrapper around a **public Google Drive folder** of event photos.

- **Organizer** pastes a Drive folder link → gets an event link + QR.
- **Attendee** opens the link → takes a selfie → sees **only the photos they appear in** → taps to open/download the original from Drive.

We never store or serve photo files. We store only face embeddings + Drive file IDs. Selfies are never written to disk.

## 2. Stack (fixed — do not change)

| Layer | Choice |
|---|---|
| Language | Python 3.12 |
| Web | FastAPI + uvicorn (single process) |
| Faces | `opencv-python-headless` (>=4.9): `cv2.FaceDetectorYN` (YuNet) + `cv2.FaceRecognizerSF` (SFace) |
| Math | numpy |
| HTTP client | httpx |
| DB | SQLite (stdlib `sqlite3`, WAL mode) |
| QR | `segno` (pure Python) |
| Frontend | 3 static HTML files, vanilla JS + inline CSS. No build step, no framework, no CDN deps |
| Runtime | Docker Compose (runs on OrbStack, Mac mini, arm64) |
| Public HTTPS | `cloudflare/cloudflared` tunnel container (HTTPS is required for camera access) |

Models (download in Dockerfile, verify file size > 100 KB to avoid Git-LFS pointer files):
- `https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx` (MIT)
- `https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx` (Apache-2.0)

## 3. Actions (complete list — build exactly these)

**Organizer**
1. Create event (Drive folder URL + optional name)
2. Get event link + QR
3. View indexing progress
4. Delete event

**Attendee**
1. Open event link (phone or laptop)
2. Take selfie (front camera / webcam) or upload a photo
3. Retake
4. View matched photos
5. Open / download original from Drive

**System**
1. Validate link (extract folder ID, confirm public)
2. List folder recursively (images only)
3. Index: fetch → detect → align → embed → store
4. Resume unfinished indexing on startup
5. Incremental sync of new photos when event is opened (max once / 10 min)
6. Match selfie; discard selfie
7. Auto-expire events after `RETENTION_DAYS`
8. Per-IP rate limiting

## 4. Repo layout

```
identipix/
  app/
    main.py        # FastAPI app, routes, static serving, startup tasks
    config.py      # env settings
    db.py          # sqlite schema + queries
    drive.py       # parse_folder_id(), check_folder(), list_images(), fetch_image()
    faces.py       # detect(), embed(), Matcher
    indexer.py     # background indexing/sync jobs
    ratelimit.py   # tiny in-memory per-IP limiter
    static/
      index.html   # create event
      event.html   # attendee
      admin.html   # organizer admin
  models/          # populated by Dockerfile
  eval/eval.py     # precision/recall script
  tests/           # pytest
  Dockerfile
  compose.yml
  .env.example
  README.md
  LICENSE          # MIT
```

## 5. Config (`.env`)

```
GOOGLE_API_KEY=            # required, Drive API v3 enabled, no OAuth
PUBLIC_BASE_URL=           # e.g. https://photos.example.com (used in links/QR)
TUNNEL_TOKEN=              # cloudflared tunnel token
DATA_DIR=/data
RETENTION_DAYS=30
MATCH_THRESHOLD=0.363      # SFace cosine threshold (tune with eval)
DETECT_SCORE=0.8           # YuNet confidence
MIN_FACE_PX=24             # ignore smaller faces
INDEX_LONG_SIDE=1600       # px used for indexing
INDEX_WORKERS=8
MAX_CONCURRENT_EVENTS=2    # events indexing at once
SYNC_INTERVAL_MIN=10
MATCH_RATE_PER_MIN=10      # per IP
CREATE_RATE_PER_HOUR=5     # per IP
```

## 6. Data model (SQLite, `DATA_DIR/identipix.db`, WAL)

```sql
CREATE TABLE events(
  id TEXT PRIMARY KEY,            -- secrets.token_urlsafe(8)
  admin_token TEXT NOT NULL,      -- secrets.token_urlsafe(16)
  folder_id TEXT NOT NULL,
  name TEXT,
  status TEXT NOT NULL,           -- 'indexing' | 'ready' | 'error'
  error TEXT,
  done INTEGER DEFAULT 0,
  total INTEGER DEFAULT 0,
  last_sync INTEGER,              -- unix seconds
  created_at INTEGER NOT NULL
);
CREATE TABLE photos(              -- every processed file, even with 0 faces
  event_id TEXT, file_id TEXT, name TEXT,
  PRIMARY KEY(event_id, file_id)
);
CREATE TABLE faces(
  event_id TEXT, file_id TEXT,
  emb BLOB NOT NULL               -- 128 x float32, L2-normalized
);
CREATE INDEX faces_event ON faces(event_id);
```
Delete event = delete rows from all three tables.

## 7. Drive integration (`drive.py`)

- `parse_folder_id(url)`: accept `https://drive.google.com/drive/folders/{ID}`, `.../drive/u/0/folders/{ID}`, `?id={ID}`, or a bare ID. Strip query params like `?usp=sharing`.
- `check_folder(id)`: `GET https://www.googleapis.com/drive/v3/files/{id}?fields=id,name,mimeType&supportsAllDrives=true&key=KEY`. 404/403 → error "Folder not found or not public. Share it as 'Anyone with the link'". mimeType must be `application/vnd.google-apps.folder`.
- `list_images(id)`: `GET .../drive/v3/files` with `q="'{id}' in parents and trashed=false"`, `fields=nextPageToken,files(id,name,mimeType,thumbnailLink)`, `pageSize=1000`, `supportsAllDrives=true`, `includeItemsFromAllDrives=true`. Paginate. Recurse into subfolders. Keep `mimeType` starting with `image/`.
- `fetch_image(file)`: primary = `thumbnailLink` with its trailing `=s\d+` replaced by `=s{INDEX_LONG_SIDE}` (returns JPEG, also handles HEIC). Fallback if missing/failed = `GET .../drive/v3/files/{id}?alt=media&key=KEY`. Retry 429/5xx with exponential backoff (3 tries). Decode with `cv2.imdecode`; downscale so long side ≤ `INDEX_LONG_SIDE`.

## 8. Faces (`faces.py`)

- One `FaceDetectorYN` + `FaceRecognizerSF` **per thread** (`threading.local`) — they are not thread-safe.
- `detect(img)`: `det.setInputSize((w,h))`, `det.setScoreThreshold(DETECT_SCORE)`, `_, faces = det.detect(img)`; drop faces with width or height < `MIN_FACE_PX`.
- `embed(img, face_row)`: `aligned = rec.alignCrop(img, face_row)`; `f = rec.feature(aligned).flatten().astype(float32)`; return `f / norm(f)`.
- `Matcher`: in-memory cache `event_id -> (count, matrix[N,128], file_ids[N])`. Rebuild when `SELECT COUNT(*) FROM faces WHERE event_id=?` differs from cached count.
- `match(event_id, selfie_emb)`: `scores = matrix @ selfie_emb`; per file_id keep max score; return those ≥ `MATCH_THRESHOLD`, sorted desc.

## 9. Indexer (`indexer.py`)

- `start_index(event_id)`: runs in a background thread; global `threading.Semaphore(MAX_CONCURRENT_EVENTS)`.
- Steps: `list_images` → skip file_ids already in `photos` → set `total` = all images, `done` = already processed → `ThreadPoolExecutor(INDEX_WORKERS)` over new files: fetch, detect, embed, then in one transaction insert into `photos` + `faces` and increment `done`. A single file failing is logged and still recorded in `photos` (so it's not retried forever) — do not fail the event.
- End: `status='ready'`, `last_sync=now`. Listing failure → `status='error'`, `error=<message>`.
- Startup: for every event with `status='indexing'`, call `start_index` (resume).
- Sync: on `GET /api/events/{id}`, if `status='ready'` and `now - last_sync > SYNC_INTERVAL_MIN`, set `status='indexing'` and `start_index` (incremental by design).
- Expiry: on startup and hourly, delete events with `created_at < now - RETENTION_DAYS`.
- Guard so an event is never indexed by two threads at once (a set of active event_ids under a lock).

## 10. HTTP API (`main.py`)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/` | – | `index.html` |
| GET | `/e/{id}` | – | `event.html` (404 page if unknown) |
| GET | `/a/{id}` | – | `admin.html` (token checked by API calls) |
| POST | `/api/events` | JSON `{folder_url, name?}` | `201 {id, admin_token, event_url, admin_url}`; validates folder first, then starts indexing |
| GET | `/api/events/{id}` | – | `{name, status, done, total, error}` (may trigger sync) |
| POST | `/api/events/{id}/match` | multipart `selfie` (≤5 MB) | `{photos:[{file_id, name, score}]}` |
| GET | `/api/events/{id}/qr.svg?t=` | – | SVG QR of `event_url` (admin token required) |
| DELETE | `/api/events/{id}?t=` | – | `204` |

Match rules:
- Read upload into memory only. Never write to disk. Never log image bytes.
- Downscale to long side 1024, detect. 0 faces → `422 {"error":"no_face"}`. >1 face → use the largest.
- Allowed while `status='indexing'` (matches against what's indexed so far).

Other:
- Admin token compare with `secrets.compare_digest`.
- Rate limits: client IP = `CF-Connecting-IP` header, else socket IP. Exceed → `429`.
- Unknown event → `404`.

## 11. Frontend (vanilla, mobile-first, single column, max-width 640px)

**`index.html` (create)**
- Input: Drive folder URL, optional event name, "Create" button.
- On success → redirect to `admin_url`. On error show the message inline.

**`admin.html` (organizer)**
- Read `t` from query string. Poll `GET /api/events/{id}` every 2s while `indexing`.
- Show: name, progress bar `done/total`, status, error.
- Show event link with "Copy" button and the QR (`<img src="/api/events/{id}/qr.svg?t=...">`).
- "Delete event" button with `confirm()` → DELETE → show "Deleted".
- Tell the organizer to bookmark this page (it's the only admin access).

**`event.html` (attendee)**
- Header: event name. If indexing, show "Still processing photos (x/y) — results may be incomplete".
- Camera:
  - `navigator.mediaDevices.getUserMedia({video:{facingMode:"user", width:{ideal:1280}}, audio:false})` into `<video playsinline autoplay muted>`, mirrored via CSS `transform: scaleX(-1)`.
  - "Take selfie" → draw frame to canvas (unmirrored), scale long side to 640, `canvas.toBlob(..., "image/jpeg", 0.85)` → POST.
  - Stop camera tracks after capture.
  - Fallback (getUserMedia missing/denied): show `<input type="file" accept="image/*">`; resize the chosen image through canvas the same way before upload.
- Results:
  - Count line: "Found you in N photos".
  - Grid (2 cols mobile, 4 desktop) of `<img loading="lazy" src="https://drive.google.com/thumbnail?id={file_id}&sz=w400">`.
  - Tap → open `https://drive.google.com/file/d/{file_id}/view` in new tab. Small "Download" link → `https://drive.google.com/uc?export=download&id={file_id}`.
  - 0 results → "No photos found. Try another selfie with good light, facing the camera."
  - "Retake" button restarts camera.
- `no_face` → "Couldn't see a face — try again."
- Footer one-liner: "Your selfie is processed in memory and never stored."

## 12. Docker

**Dockerfile**
- `python:3.12-slim`, `pip install --no-cache-dir fastapi uvicorn[standard] opencv-python-headless numpy httpx python-multipart segno`.
- Download both ONNX models into `/app/models`, fail build if either < 100 KB.
- Non-root user. `CMD uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1`.

**compose.yml**
```yaml
services:
  app:
    build: .
    env_file: .env
    volumes: ["./data:/data"]
    ports: ["8080:8080"]
    restart: unless-stopped
  tunnel:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run --token ${TUNNEL_TOKEN}
    depends_on: [app]
    restart: unless-stopped
```
(Cloudflare tunnel public hostname → `http://app:8080`.)

## 13. Tests & correctness

**pytest (`tests/`)**
- `parse_folder_id` for all URL shapes + invalid input.
- Matcher: synthetic normalized vectors → correct per-photo max and threshold cut.
- API with `drive.py` monkeypatched to a local folder of test images: create → index → status `ready` → match returns expected file → delete removes all rows.
- `faces.py` on a real sample image with a known face count.

**`eval/eval.py`**
- Input `eval/labels.json`: `{ "folder_url": "...", "people": { "<name>": { "selfie": "path.jpg", "photos": ["file_id", ...] } } }`.
- Indexes the folder, matches each selfie, prints precision / recall / F1 at thresholds 0.25→0.50 step 0.025, and the threshold with best recall at precision ≥ 0.9.

## 14. Acceptance criteria (v1 is done when)

1. `docker compose up -d` on a fresh Mac mini (OrbStack) with only `.env` filled works.
2. Creating an event from a public folder of ~500 photos completes indexing (target: under ~3 min) with progress visible.
3. A private folder link shows a clear error and creates no event.
4. On iPhone Safari, Android Chrome and desktop Chrome/Safari: camera opens to front camera/webcam, selfie → results in < 1 s server time.
5. Photos added to the folder later appear after the next sync.
6. Restarting the container mid-index resumes without re-processing finished photos.
7. Delete removes all rows; expired events are removed automatically.
8. No selfie bytes ever on disk (grep `/data` and the container FS after matching).
9. All pytest tests pass.

## 15. Day-1 risk check (do first)

Before building the rest, script a test against a real public folder:
1. Can `thumbnailLink` with `=s1600` be fetched for ~500 files without throttling?
2. Does `https://drive.google.com/thumbnail?id=...&sz=w400` load in a browser `<img>` for public files?

If (1) fails → use the `alt=media` fallback as primary. If (2) fails → add `GET /api/thumb/{event_id}/{file_id}` that proxies `thumbnailLink` (`=s400`) with `Cache-Control: public, max-age=86400`, and point the grid at it.

## 16. Out of scope for v1

Accounts, OAuth, non-Drive providers, zip/bulk download, branding, analytics, email, multiple selfies, video, GPU, any database other than SQLite, any JS framework.