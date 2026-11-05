import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import config, db, drive, faces, indexer

CROWD = Path(__file__).parent / "data" / "crowd.jpg"
FOLDER = "1AbCdEfGhIjKlMnOp"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://x.test")
    crowd = cv2.imread(str(CROWD))
    blank = np.full((400, 600, 3), 127, np.uint8)
    images = {"crowd": crowd, "blank": blank}
    files = [{"id": k, "name": f"{k}.jpg"} for k in images]
    monkeypatch.setattr(drive, "check_folder", lambda fid: "Test folder")
    monkeypatch.setattr(drive, "list_images", lambda fid: list(files))
    monkeypatch.setattr(drive, "fetch_image", lambda f: images[f["id"]])
    from app import main
    main.limiter.__init__()
    with TestClient(main.app) as c:
        c.images, c.files = images, files
        yield c
        for _ in range(300):  # let background indexing finish before the temp DB goes away
            if not indexer._active:
                break
            time.sleep(0.1)


def _wait_ready(c, eid):
    for _ in range(300):
        d = c.get(f"/api/events/{eid}").json()
        if d["status"] != "indexing":
            return d
        time.sleep(0.1)
    raise AssertionError("indexing timed out")


def _selfie_jpeg(c):
    img = c.images["crowd"]
    small = cv2.resize(img, (1024, int(1024 * img.shape[0] / img.shape[1])))
    row = faces.largest(faces.detect(small))
    x, y, w, h = [int(v) for v in row[:4]]
    pad = int(w * 0.6)
    crop = small[max(0, y - pad): y + h + pad, max(0, x - pad): x + w + pad]
    return cv2.imencode(".jpg", crop)[1].tobytes()


def test_full_flow(client, monkeypatch):
    r = client.post("/api/events", json={"folder_url": f"https://drive.google.com/drive/folders/{FOLDER}?usp=sharing"})
    assert r.status_code == 201
    ev = r.json()
    eid, tok = ev["id"], ev["admin_token"]
    assert ev["event_url"] == f"https://x.test/e/{eid}"
    assert ev["admin_url"] == f"https://x.test/a/{eid}?t={tok}"

    d = _wait_ready(client, eid)
    assert d["status"] == "ready" and d["done"] == d["total"] == 2 and d["name"] == "Test folder"

    r = client.post(f"/api/events/{eid}/match", files={"selfie": ("s.jpg", _selfie_jpeg(client), "image/jpeg")})
    assert r.status_code == 200
    photos = r.json()["photos"]
    assert [p["file_id"] for p in photos] == ["crowd"]
    assert photos[0]["score"] > 0.9

    # no face -> 422
    blank = cv2.imencode(".jpg", client.images["blank"])[1].tobytes()
    r = client.post(f"/api/events/{eid}/match", files={"selfie": ("s.jpg", blank, "image/jpeg")})
    assert r.status_code == 422 and r.json() == {"error": "no_face"}

    # thumbnail proxy: cached, event photos only
    monkeypatch.setattr(drive, "fetch_thumb", lambda fid: b"jpegbytes")
    r = client.get(f"/api/thumb/{eid}/crowd")
    assert r.status_code == 200 and r.content == b"jpegbytes" and "max-age" in r.headers["cache-control"]
    assert client.get(f"/api/thumb/{eid}/not-in-event").status_code == 404

    # admin endpoints need token
    assert client.get(f"/api/events/{eid}/qr.svg?t=wrong").status_code == 403
    qr = client.get(f"/api/events/{eid}/qr.svg?t={tok}")
    assert qr.status_code == 200 and b"<svg" in qr.content
    assert client.delete(f"/api/events/{eid}?t=wrong").status_code == 403

    assert client.delete(f"/api/events/{eid}?t={tok}").status_code == 204
    with db.conn() as c:
        for t in ("events", "photos", "faces"):
            assert c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
    assert client.get(f"/api/events/{eid}").status_code == 404
    assert client.get(f"/e/{eid}").status_code == 404


def test_bad_folder_creates_nothing(client, monkeypatch):
    def boom(fid):
        raise drive.DriveError(drive.NOT_PUBLIC)
    monkeypatch.setattr(drive, "check_folder", boom)
    r = client.post("/api/events", json={"folder_url": FOLDER})
    assert r.status_code == 400 and "not public" in r.json()["detail"]
    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_failed_file_is_recorded_not_retried(client, monkeypatch):
    def fetch(f):
        if f["id"] == "blank":
            raise drive.DriveError("boom")
        return client.images[f["id"]]
    monkeypatch.setattr(drive, "fetch_image", fetch)
    eid = client.post("/api/events", json={"folder_url": FOLDER}).json()["id"]
    assert _wait_ready(client, eid)["status"] == "ready"
    assert db.processed_file_ids(eid) == {"crowd", "blank"}


def test_incremental_sync_and_resume(client, monkeypatch):
    eid = client.post("/api/events", json={"folder_url": FOLDER}).json()["id"]
    _wait_ready(client, eid)
    calls = []
    orig = drive.fetch_image
    monkeypatch.setattr(drive, "fetch_image", lambda f: (calls.append(f["id"]), orig(f))[1])
    client.files.append({"id": "new", "name": "new.jpg"})
    client.images["new"] = client.images["blank"]
    db.update_event(eid, last_sync=int(time.time()) - 3600)  # stale -> next open syncs
    client.get(f"/api/events/{eid}")
    assert _wait_ready(client, eid)["total"] == 3
    assert calls == ["new"]  # finished photos not reprocessed
    # resume: an 'indexing' event found at startup is picked up and nothing is redone
    calls.clear()
    db.update_event(eid, status="indexing")
    indexer.resume_all()
    assert _wait_ready(client, eid)["status"] == "ready" and calls == []


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(config, "CREATE_RATE_PER_HOUR", 2)
    codes = [client.post("/api/events", json={"folder_url": FOLDER}).status_code for _ in range(3)]
    assert codes == [201, 201, 429]


def test_unknown_event_404(client):
    assert client.get("/api/events/nope").status_code == 404
