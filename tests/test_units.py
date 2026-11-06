from pathlib import Path

import cv2
import numpy as np
import pytest

from app import config, db, drive, faces

CROWD = Path(__file__).parent / "data" / "crowd.jpg"


@pytest.mark.parametrize("url", [
    "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOp",
    "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOp?usp=sharing",
    "https://drive.google.com/drive/u/0/folders/1AbCdEfGhIjKlMnOp",
    "https://drive.google.com/open?id=1AbCdEfGhIjKlMnOp",
    "1AbCdEfGhIjKlMnOp",
    "  1AbCdEfGhIjKlMnOp  ",
])
def test_parse_ok(url):
    assert drive.parse_folder_id(url) == "1AbCdEfGhIjKlMnOp"


@pytest.mark.parametrize("url", ["", "hello world", "https://example.com/x", "short"])
def test_parse_invalid(url):
    with pytest.raises(drive.DriveError):
        drive.parse_folder_id(url)


def _unit(v):
    v = np.array(v, np.float32)
    return v / np.linalg.norm(v)


def test_matcher_max_per_photo_and_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    db.init()
    db.create_event("e", "tok", "f", "n")
    rng = np.random.default_rng(0)
    me = _unit(rng.normal(size=128))
    other = _unit(rng.normal(size=128))
    near = _unit(me + 0.05 * rng.normal(size=128))
    db.record_photo("e", "p1", "p1", [other, near])   # two faces; best should be `near`
    db.record_photo("e", "p2", "p2", [other])         # below threshold
    db.record_photo("e", "p3", "p3", [me])            # exact
    db.record_photo("e", "p4", "p4", [])              # no faces
    res = faces.Matcher().match("e", me)
    assert [f for f, _ in res] == ["p3", "p1"]
    assert res[0][1] == pytest.approx(1.0, abs=1e-5)
    assert res[1][1] == pytest.approx(float(near @ me), abs=1e-5)


def test_matcher_rebuilds_when_count_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    db.init()
    db.create_event("e", "tok", "f", "n")
    me = _unit(np.random.default_rng(1).normal(size=128))
    m = faces.Matcher()
    assert m.match("e", me) == []
    db.record_photo("e", "p1", "p1", [me])
    assert [f for f, _ in m.match("e", me)] == ["p1"]


def test_detect_known_face_count():
    img = cv2.imread(str(CROWD))
    img = cv2.resize(img, (1024, int(1024 * img.shape[0] / img.shape[1])))
    found = faces.detect(img)
    assert len(found) == 23  # measured once on this sample; guards against regressions
    e = faces.embed(img, faces.largest(found))
    assert e.shape == (128,) and np.linalg.norm(e) == pytest.approx(1.0, abs=1e-4)


def test_embed_selfie_is_unit_and_close_to_plain_embed():
    img = cv2.imread(str(CROWD))
    img = cv2.resize(img, (1024, int(1024 * img.shape[0] / img.shape[1])))
    row = faces.largest(faces.detect(img))
    a, b = faces.embed(img, row), faces.embed_selfie(img, row)
    assert np.linalg.norm(b) == pytest.approx(1.0, abs=1e-4)
    assert float(a @ b) > 0.8


def test_check_models_fails_loudly_when_models_are_missing(tmp_path, monkeypatch):
    import threading
    monkeypatch.setattr(config, "MODELS_DIR", tmp_path)  # empty folder
    errors = []

    def run():  # models are cached per thread, so use a fresh one
        try:
            faces.check_models()
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=run); t.start(); t.join()
    assert errors, "a missing model must raise, not be skipped"


# ---- Drive edge cases: videos, odd formats, bad files ----
class _Resp:
    def __init__(self, code=200, content=b"", data=None):
        self.status_code, self.content, self._data = code, content, data

    def json(self):
        return self._data


def test_list_images_skips_non_photos_and_follows_pages_and_folders(monkeypatch):
    pages = {
        ("root", None): {"nextPageToken": "p2", "files": [
            {"id": "v", "name": "clip.mp4", "mimeType": "video/mp4"},
            {"id": "d", "name": "a.pdf", "mimeType": "application/pdf"},
            {"id": "g", "name": "sheet", "mimeType": "application/vnd.google-apps.spreadsheet"},
            {"id": "s", "name": "link", "mimeType": "application/vnd.google-apps.shortcut"},
            {"id": "i1", "name": "a.jpg", "mimeType": "image/jpeg"},
            {"id": "sub", "name": "Day 2", "mimeType": "application/vnd.google-apps.folder"}]},
        ("root", "p2"): {"files": [
            {"id": "i2", "name": "b.heic", "mimeType": "image/heic"},
            {"id": "au", "name": "s.mp3", "mimeType": "audio/mpeg"}]},
        ("sub", None): {"files": [
            {"id": "i3", "name": "c.webp", "mimeType": "image/webp"},
            {"id": "v2", "name": "m.mov", "mimeType": "video/quicktime"}]},
    }
    monkeypatch.setattr(drive, "_get", lambda url, **kw: _Resp(data=pages[(kw["params"]["q"].split("'")[1], kw["params"].get("pageToken"))]))
    assert sorted(f["name"] for f in drive.list_images("root")) == ["a.jpg", "b.heic", "c.webp"]


@pytest.mark.parametrize("content", [b"", b"not an image at all"])
def test_undecodable_files_raise_drivererror_not_a_crash(monkeypatch, content):
    monkeypatch.setattr(drive, "_get", lambda url, **kw: _Resp(200, content))
    with pytest.raises(drive.DriveError):
        drive.fetch_image({"id": "x", "name": "bad.jpg"})


def test_huge_original_without_a_preview_is_skipped(monkeypatch):
    called = []
    monkeypatch.setattr(drive, "_get", lambda url, **kw: called.append(url) or _Resp(200, b"x"))
    big = {"id": "x", "name": "huge.tif", "size": str((config.MAX_DOWNLOAD_MB + 1) * 1024 * 1024)}
    with pytest.raises(drive.DriveError, match="too large"):
        drive.fetch_image(big)
    assert called == []  # never even started the download
