"""Precision/recall of face matching at different thresholds.

Usage (from repo root, with GOOGLE_API_KEY set):
    python -m eval.eval eval/labels.json
labels.json: {"folder_url": "...", "people": {"<name>": {"selfie": "path.jpg", "photos": ["file_id", ...]}}}
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from app import config, drive, faces


def best_scores(selfie_emb, photo_embs):
    """file_id -> best cosine score against the selfie."""
    return {fid: max(float(e @ selfie_emb) for e in embs) for fid, embs in photo_embs.items() if embs}


def main(path: str) -> None:
    labels = json.load(open(path))
    files = drive.list_images(drive.parse_folder_id(labels["folder_url"]))
    print(f"indexing {len(files)} photos...", file=sys.stderr)

    def work(f):
        try:
            img = drive.fetch_image(f)
            return f["id"], [faces.embed(img, r) for r in faces.detect(img)]
        except Exception as e:
            print(f"skip {f['id']}: {e}", file=sys.stderr)
            return f["id"], []

    with ThreadPoolExecutor(config.INDEX_WORKERS) as pool:
        photo_embs = dict(pool.map(work, files))

    people = {}
    for name, p in labels["people"].items():
        img = cv2.imread(p["selfie"])
        found = faces.detect(img)
        if len(found) == 0:
            print(f"no face in selfie for {name}, skipped", file=sys.stderr)
            continue
        people[name] = (best_scores(faces.embed(img, faces.largest(found)), photo_embs), set(p["photos"]))

    print("threshold  precision  recall  f1")
    best = None
    for th in np.arange(0.25, 0.5001, 0.025):
        tp = fp = fn = 0
        for scores, truth in people.values():
            pred = {f for f, s in scores.items() if s >= th}
            tp += len(pred & truth)
            fp += len(pred - truth)
            fn += len(truth - pred)
        prec = tp / (tp + fp) if tp + fp else 1.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        print(f"{th:9.3f}  {prec:9.3f}  {rec:6.3f}  {f1:.3f}")
        if prec >= 0.9 and (best is None or rec > best[1]):
            best = (th, rec, prec)
    if best:
        print(f"\nbest recall at precision >= 0.9: threshold {best[0]:.3f} (recall {best[1]:.3f}, precision {best[2]:.3f})")
    else:
        print("\nno threshold reaches precision >= 0.9")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
