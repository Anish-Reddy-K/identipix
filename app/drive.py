import re
import time

import cv2
import httpx
import numpy as np

from . import config

API = "https://www.googleapis.com/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"
NOT_PUBLIC = "Folder not found or not public. Share it as 'Anyone with the link'"
_ID = r"[A-Za-z0-9_-]{10,}"


class DriveError(Exception):
    pass


def parse_folder_id(url: str) -> str:
    url = (url or "").strip()
    if m := re.search(rf"/folders/({_ID})", url):
        return m.group(1)
    if m := re.search(rf"[?&]id=({_ID})", url):
        return m.group(1)
    if re.fullmatch(_ID, url):
        return url
    raise DriveError("That doesn't look like a Google Drive folder link")


def _get(url: str, **kw) -> httpx.Response:
    """GET with exponential backoff on 429/5xx and network errors (3 tries)."""
    for attempt in range(3):
        try:
            r = httpx.get(url, timeout=30, follow_redirects=True, **kw)
            if r.status_code not in (429, 500, 502, 503, 504):
                return r
        except httpx.TransportError:
            if attempt == 2:
                raise
        time.sleep(2**attempt)
    return r


def check_folder(folder_id: str) -> str:
    """Returns the folder name, or raises DriveError."""
    r = _get(
        f"{API}/{folder_id}",
        params={"fields": "id,name,mimeType", "supportsAllDrives": "true", "key": config.GOOGLE_API_KEY},
    )
    if r.status_code in (403, 404):
        raise DriveError(NOT_PUBLIC)
    if r.status_code != 200:
        raise DriveError(f"Google Drive error ({r.status_code})")
    data = r.json()
    if data.get("mimeType") != FOLDER_MIME:
        raise DriveError("That link is not a folder")
    return data.get("name", "")


def list_images(folder_id: str) -> list[dict]:
    images, stack, seen = [], [folder_id], set()
    while stack:
        fid = stack.pop()
        if fid in seen:
            continue
        seen.add(fid)
        token = None
        while True:
            params = {
                "q": f"'{fid}' in parents and trashed=false",
                "fields": "nextPageToken,files(id,name,mimeType,thumbnailLink)",
                "pageSize": 1000,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "key": config.GOOGLE_API_KEY,
            }
            if token:
                params["pageToken"] = token
            r = _get(API, params=params)
            if r.status_code != 200:
                raise DriveError(f"Could not list folder ({r.status_code})")
            data = r.json()
            for f in data.get("files", []):
                mt = f.get("mimeType", "")
                if mt == FOLDER_MIME:
                    stack.append(f["id"])
                elif mt.startswith("image/"):
                    images.append(f)
            token = data.get("nextPageToken")
            if not token:
                break
    return images


def _decode(content: bytes):
    img = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    s = config.INDEX_LONG_SIDE / max(h, w)
    if s < 1:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return img


def fetch_image(file: dict):
    """Returns a BGR image, or raises DriveError."""
    thumb = file.get("thumbnailLink")
    if thumb:
        url = re.sub(r"=s\d+$", f"=s{config.INDEX_LONG_SIDE}", thumb)
        try:
            r = _get(url)
            if r.status_code == 200 and (img := _decode(r.content)) is not None:
                return img
        except httpx.HTTPError:
            pass
    r = _get(f"{API}/{file['id']}", params={"alt": "media", "key": config.GOOGLE_API_KEY})
    if r.status_code != 200:
        raise DriveError(f"Could not download {file.get('name')} ({r.status_code})")
    img = _decode(r.content)
    if img is None:
        raise DriveError(f"Could not decode {file.get('name')}")
    return img
