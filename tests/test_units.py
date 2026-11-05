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
