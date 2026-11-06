import asyncio
import io
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import numpy as np
import segno
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from . import config, db, drive, faces, indexer
from .ratelimit import RateLimiter

STATIC = Path(__file__).parent / "static"
MAX_SELFIE = 5 * 1024 * 1024
matcher = faces.Matcher()
limiter = RateLimiter()
log = logging.getLogger("identipix")


async def _expiry_loop():
    while True:
        try:
            await asyncio.to_thread(indexer.expire_old, matcher)
        except Exception:
            log.exception("expiry failed")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    indexer.resume_all()
    task = asyncio.create_task(_expiry_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


def client_ip(request: Request) -> str:
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "unknown")


def _event_or_404(event_id: str):
    ev = db.get_event(event_id)
    if ev is None:
        raise HTTPException(404, "Event not found")
    return ev


def _check_token(ev, t: str | None) -> None:
    if not t or not secrets.compare_digest(t, ev["admin_token"]):
        raise HTTPException(403, "Invalid admin token")


def _base(request: Request) -> str:
    return config.PUBLIC_BASE_URL or str(request.base_url).rstrip("/")


@app.get("/healthz")
def healthz():
    db.get_event("healthz")  # touches the database, so "ok" means the whole app works
    return {"ok": True}


# ---- pages ----
@app.get("/")
def index_page():
    return FileResponse(STATIC / "index.html")


@app.get("/e/{event_id}")
def event_page(event_id: str):
    if db.get_event(event_id) is None:
        return HTMLResponse("<h1>Event not found</h1><p>It may have expired or been deleted.</p>", status_code=404)
    return FileResponse(STATIC / "event.html")


@app.get("/a/{event_id}")
def admin_page(event_id: str):
    return FileResponse(STATIC / "admin.html")


# ---- api ----
@app.post("/api/events", status_code=201)
def create_event(request: Request, body: dict):
    if not limiter.allow("create", client_ip(request), config.CREATE_RATE_PER_HOUR, 3600):
        raise HTTPException(429, "Too many requests, try again later")
    try:
        folder_id = drive.parse_folder_id(str(body.get("folder_url", "")))
        folder_name = drive.check_folder(folder_id)
    except drive.DriveError as e:
        raise HTTPException(400, str(e))
    name = (str(body.get("name") or "").strip() or folder_name)[:100]
    event_id, token = secrets.token_urlsafe(8), secrets.token_urlsafe(16)
    db.create_event(event_id, token, folder_id, name)
    indexer.start_index(event_id)
    base = _base(request)
    return {
        "id": event_id,
        "admin_token": token,
        "event_url": f"{base}/e/{event_id}",
        "admin_url": f"{base}/a/{event_id}?t={token}",
    }


@app.get("/api/events/{event_id}")
def get_event(event_id: str):
    ev = _event_or_404(event_id)
    indexer.maybe_sync(ev)
    ev = db.get_event(event_id)
    return {
        **{k: ev[k] for k in ("name", "status", "done", "total", "error")},
        "folder_url": f"https://drive.google.com/drive/folders/{ev['folder_id']}",
        "highlights": db.list_highlights(event_id),
    }


@app.get("/api/events/{event_id}/photos")
def list_event_photos(event_id: str, t: str = ""):
    _check_token(_event_or_404(event_id), t)
    return {"photos": db.list_photos(event_id)}


@app.put("/api/events/{event_id}/highlights")
def put_highlights(event_id: str, body: dict, t: str = ""):
    _check_token(_event_or_404(event_id), t)
    ids = body.get("file_ids")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids) or len(ids) > 1000:
        raise HTTPException(400, "file_ids must be a list of ids")
    db.set_highlights(event_id, ids)
    return {"highlights": db.list_highlights(event_id)}


@app.post("/api/events/{event_id}/match")
def match(event_id: str, request: Request, selfie: UploadFile = File(...), consent: str = Form("")):
    if consent != "yes":  # the page asks before the selfie; the server insists, so there is no way around it
        return JSONResponse({"error": "consent_required"}, status_code=400)
    if not limiter.allow("match", client_ip(request), config.MATCH_RATE_PER_MIN, 60):
        raise HTTPException(429, "Too many requests, try again in a minute")
    _event_or_404(event_id)
    data = selfie.file.read(MAX_SELFIE + 1)
    if len(data) > MAX_SELFIE:
        raise HTTPException(413, "Selfie too large (max 5 MB)")
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not read image")
    h, w = img.shape[:2]
    s = 1024 / max(h, w)
    if s < 1:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    found = faces.detect(img)
    if len(found) == 0:
        return JSONResponse({"error": "no_face"}, status_code=422)
    results = matcher.match(event_id, faces.embed_selfie(img, faces.largest(found)))
    names = db.photo_names(event_id, [f for f, _ in results])
    items = [{"file_id": f, "name": names.get(f, ""), "score": round(s, 4)} for f, s in results]
    return {
        "photos": [i for i in items if i["score"] >= config.STRONG_THRESHOLD],
        "maybe": [i for i in items if i["score"] < config.STRONG_THRESHOLD],
    }


@app.get("/api/thumb/{event_id}/{file_id}")
def thumb(event_id: str, file_id: str, s: int = 400):
    _event_or_404(event_id)
    if s not in (400, 2048):  # grid thumbnail, or large version for "save to phone"
        raise HTTPException(400, "Unsupported size")
    if not db.has_photo(event_id, file_id):  # only photos of this event, never an open proxy
        raise HTTPException(404, "Photo not found")
    try:
        data = drive.fetch_thumb(file_id, s)
    except Exception:
        raise HTTPException(502, "Thumbnail unavailable")
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/events/{event_id}/qr.svg")
def qr(event_id: str, request: Request, t: str = ""):
    ev = _event_or_404(event_id)
    _check_token(ev, t)
    buf = io.BytesIO()
    segno.make(f"{_base(request)}/e/{event_id}").save(buf, kind="svg", scale=8, border=2)
    return Response(buf.getvalue(), media_type="image/svg+xml")


@app.delete("/api/events/{event_id}", status_code=204)
def delete_event(event_id: str, t: str = ""):
    ev = _event_or_404(event_id)
    _check_token(ev, t)
    db.delete_event(event_id)
    matcher.forget(event_id)
    return Response(status_code=204)


app.mount("/static", StaticFiles(directory=STATIC), name="static")  # brand.css, logo, fonts
