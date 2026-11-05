import threading

import cv2
import numpy as np

from . import config, db

_local = threading.local()


def _models():
    if not hasattr(_local, "det"):
        _local.det = cv2.FaceDetectorYN.create(
            str(config.MODELS_DIR / "face_detection_yunet_2023mar.onnx"), "", (320, 320), config.DETECT_SCORE
        )
        _local.rec = cv2.FaceRecognizerSF.create(
            str(config.MODELS_DIR / "face_recognition_sface_2021dec.onnx"), ""
        )
    return _local.det, _local.rec


def detect(img) -> np.ndarray:
    """Rows of YuNet output (x,y,w,h,landmarks...,score), small faces dropped."""
    det, _ = _models()
    h, w = img.shape[:2]
    det.setInputSize((w, h))
    det.setScoreThreshold(config.DETECT_SCORE)
    _, faces = det.detect(img)
    if faces is None:
        return np.zeros((0, 15), np.float32)
    keep = [f for f in faces if f[2] >= config.MIN_FACE_PX and f[3] >= config.MIN_FACE_PX]
    return np.array(keep, dtype=np.float32).reshape(-1, 15)


def embed(img, face_row) -> np.ndarray:
    _, rec = _models()
    aligned = rec.alignCrop(img, face_row)
    f = rec.feature(aligned).flatten().astype(np.float32)
    return f / np.linalg.norm(f)


def embed_selfie(img, face_row) -> np.ndarray:
    """Like embed(), but averaged with the mirrored face: steadier for a single odd photo."""
    _, rec = _models()
    aligned = rec.alignCrop(img, face_row)
    out = np.zeros(128, np.float32)
    for crop in (aligned, cv2.flip(aligned, 1)):
        f = rec.feature(crop).flatten().astype(np.float32)
        out += f / np.linalg.norm(f)
    return out / np.linalg.norm(out)


def largest(faces: np.ndarray):
    return faces[np.argmax(faces[:, 2] * faces[:, 3])]


class Matcher:
    def __init__(self):
        self._cache: dict[str, tuple[int, np.ndarray, list[str]]] = {}
        self._lock = threading.Lock()

    def _get(self, event_id: str):
        count = db.face_count(event_id)
        with self._lock:
            hit = self._cache.get(event_id)
            if hit and hit[0] == count:
                return hit
            mat, ids = db.load_faces(event_id)
            hit = (count, mat, ids)
            self._cache[event_id] = hit
            return hit

    def forget(self, event_id: str) -> None:
        with self._lock:
            self._cache.pop(event_id, None)

    def match(self, event_id: str, selfie_emb: np.ndarray) -> list[tuple[str, float]]:
        _, mat, ids = self._get(event_id)
        if not ids:
            return []
        scores = mat @ selfie_emb
        best: dict[str, float] = {}
        for fid, s in zip(ids, scores):
            if s > best.get(fid, -2.0):
                best[fid] = float(s)
        out = [(f, s) for f, s in best.items() if s >= config.MATCH_THRESHOLD]
        return sorted(out, key=lambda x: -x[1])
